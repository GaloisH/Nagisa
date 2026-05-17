// MyWebSocketHandler.java
package com.wyx.neuroguiagent.handler;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.util.StrUtil;
import cn.hutool.json.JSONUtil;
import com.fasterxml.jackson.databind.ser.Serializers;
import com.wyx.neuroguiagent.agent.ChatAgent;
import com.wyx.neuroguiagent.agent.GuiAgent;
import com.wyx.neuroguiagent.common.Action;
import com.wyx.neuroguiagent.common.BaseRequest;
import com.wyx.neuroguiagent.common.BaseResponse;
import com.wyx.neuroguiagent.service.ChatNeuroService;
import com.wyx.neuroguiagent.utils.BaseContext;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.ai.chat.messages.Message;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.ConcurrentWebSocketSessionDecorator;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.*;

@Slf4j
@Component
public class MyWebSocketHandler extends TextWebSocketHandler {

    // 所有会话的历史消息管理
    private static final Map<String, List<Message>> chatHistoryManager = new ConcurrentHashMap<>();

    // 存储所有向客户端发起执行指令的Request对应的Future对象，对应会话的线程在发完消息后陷入等待，客户端对该callId进行回应后被唤醒
    private static final Map<String, CompletableFuture<String>> pendingRequests = new ConcurrentHashMap<>();
    
    // ✅ 存储所有活跃的WebSocket会话
    private final Map<String, WebSocketSession> sessions = new ConcurrentHashMap<>();
    
    // ✅ 定时任务执行器（用于主动推送）
    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(1);
    
    // 启动时自动开始推送任务
    public MyWebSocketHandler() {
//        startBroadcastTask();
    }

    @Resource
    private ChatAgent chatAgent;

    @Resource
    private GuiAgent guiAgent;


    
    /**
     * 连接建立时触发
     */
    @Override
    public void afterConnectionEstablished(WebSocketSession session) throws Exception {
        WebSocketSession concurrentSession = new ConcurrentWebSocketSessionDecorator(
                session, 10 * 1000,
                20 * 1024 * 1024);
        sessions.put(session.getId(), concurrentSession);
        
        log.info("客户端连接成功，sessionId: {}", session.getId());
        log.info("当前连接数: {}", sessions.size());
        
        // ✅ 立即发送欢迎消息
        sendResponse(concurrentSession, "欢迎连接WebSocket服务器！");
    }
    
    /**
     * 收到客户端消息时触发
     * 注意：这不是HTTP请求，而是WebSocket消息
     */
    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {

        // 0.拿到线程安全 session，转json为BaseRequest
        String sessionId = session.getId();
        session = sessions.get(sessionId);
        String clientMessage = message.getPayload();
        BaseRequest request = JSONUtil.toBean(clientMessage, BaseRequest.class);

        // 1.如果不是用户 chat 请求，则为服务端要求客户端执行动作的回应，直接处理，唤醒线程后返回
        if (!request.getType().equals("chat")){
            String callId = request.getCallId();
            if (StrUtil.isBlank(callId)){
                log.error("请求类型{},sessionId{},但 callId 为空", request.getType(), session.getId());
                return;
            }
            // callId 不为空则取出对应的Future对象
            CompletableFuture<String> future = pendingRequests.get(callId);
            if (future == null){
                log.error("不存在等待对应 callId 的线程，sessionId{},callId{}",session.getId(),callId);
                return;
            }
            // callId不为空，对应Future存在，则唤醒等待线程，流程结束
            if (request.getCode() == null || request.getCode() != 200){
                log.error("callId {}响应失败，响应码{}", callId, request.getCode());
                future.completeExceptionally(new CompletionException(request.getData(),new RuntimeException()));
                return;
            }
            future.complete(request.getData());
            log.info("callId {} 成功响应，对应等待线程已唤醒", callId);
            return;
        }
        // 2. chat 逻辑
        String chatMessage = request.getData();
        // 已废弃// 版本一: 直接调用 agent，每个步骤都给客户端 sendMessage，同步调用，先跑通流程
        // 版本二：用chatAgent模型调用对话，对话中chatAgent可将guiAgent作为工具异步执行后返回
        WebSocketSession finalSession = session;
        CompletableFuture.runAsync(()->{
            String result = chatAgent.runTask(chatMessage, finalSession);
            sendResponse(finalSession, result);
        });

    }
    
    /**
     * 连接关闭时触发
     */
    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) throws Exception {
        String sessionId = session.getId();
        sessions.remove(sessionId);
        
        log.info("客户端断开连接，sessionId: {}, 关闭状态: {}", sessionId, status);
        log.info("剩余连接数: {}", sessions.size());
    }

    @Override
    public void handleTransportError(WebSocketSession session, Throwable exception) throws Exception {
        log.error("WebSocket 传输错误，sessionId: {}, 原因: {}", session.getId(), exception.getMessage());
        // 如果是因为消息太大，这里通常会打印 "The message accurately exceed the maximum allowed size"
    }

    public static List<Message> getHistoryMessages(String sessionId){
        List<Message> messages = chatHistoryManager.get(sessionId);
        if (messages == null){
            messages = new ArrayList<>();
        }
        // 这里拷贝一份记录返回，避免潜在的线程安全问题
        return new ArrayList<>(messages);
    }

    public static synchronized void updateHistoryMessages(String sessionId, List<Message> appendMessages){
        if (appendMessages == null || appendMessages.isEmpty()){
            throw new RuntimeException("无法更新历史消息，传入消息为空");
        }
        List<Message> historyMessages = getHistoryMessages(sessionId);
        if (historyMessages.isEmpty()){
            chatHistoryManager.put(sessionId, appendMessages);
        }else {
            historyMessages.addAll(appendMessages);
        }
    }

    /**
     * ✅ 核心方法：主动推送消息给客户端
     * 这是WebSocket的关键优势！
     */
    private static boolean sendMessage(WebSocketSession session, String message) {
        if (session == null ) {
            log.error("发送消息失败,session is null");
            return false;
        }
        if (!session.isOpen()) {
            log.error("发送消息失败,session is closed");
            return false;
        }
        try {
            session.sendMessage(new TextMessage(message));
            return true;
        } catch (IOException e) {
            log.error("发送消息失败", e);
            return false;
        }

    }

    public static boolean sendResponse(WebSocketSession session, String message) {
        BaseResponse response = BaseResponse.success(message);
        String jsonResponse = JSONUtil.toJsonStr(response);
        return sendMessage(session, jsonResponse);
    }

    // 发送流式响应
    public static boolean sendStreamResponse(
            WebSocketSession session,
            String chunk,
            boolean end
    ) {

        BaseResponse response = new BaseResponse();

        response.setCode(200);
        response.setMessage("OK");
        response.setType("stream");
        response.setContent(chunk);

        // 流式时为空
        response.setCallId(null);
        response.setActions(null);

        // 新增结束标识
        response.setEnd(end);

        String json = JSONUtil.toJsonStr(response);

        return sendMessage(session, json);
    }

    /**
     * 指定session对应的客户端执行指令，并阻塞等待至客户端响应指令执行结果
     * 执行成功则返回对应结果，执行失败则返回空字符串
     * @param session 客户端
     * @param content 让客户端打印的内容
     * @param actions 让客户端执行的指令
     * @return 客户端执行成功则返回对应结果，客户端执行失败则返回空字符串
     * @throws Exception
     */
    public static String sendRequestAndWait(WebSocketSession session, String content, List<Action> actions){

        // 1. 将 Future 存入等待池
        String callId = UUID.randomUUID().toString(); // 生成唯一 ID
        CompletableFuture<String> future = new CompletableFuture<>();
        pendingRequests.put(callId, future);

        // 2. 构造协议并发送
        BaseResponse response = BaseResponse.success(content, callId, actions);
        String jsonResponse = JSONUtil.toJsonStr(response);
        log.info("正在请求客户端，callId: {}, 请求内容: {}", callId, jsonResponse);


        String result = "";
        try {
            boolean isSendSuccess = sendMessage(session, jsonResponse);
            if (!isSendSuccess){
                throw new RuntimeException("消息发送失败, sessionId: " + session.getId());
            }
            // 3. 阻塞等待结果（设置超时时间，防止客户端掉线导致无限等待）
            result = future.get(30, TimeUnit.SECONDS);
            log.info("callId {} 成功响应", callId);
        } catch (Exception e) {
            // 可能是等待超时TimeoutException，可能是执行失败ExecutionException，没做区分，懒
            log.error("callId {} 响应失败", callId, e);
        } finally {
            // 4. 无论成功失败，移除记录
            pendingRequests.remove(callId);
        }
        return result;
    }
    
    /**
     * ✅ 核心方法：广播消息给所有客户端
     * 注意：这是服务端主动发起的，不是响应客户端请求！
     */
    public void broadcast(String message) {
        log.info("开始广播消息: {}", message);
        
        sessions.values().forEach(session -> {
            if (session.isOpen()) {
                try {
                    session.sendMessage(new TextMessage(message));
                } catch (IOException e) {
                    log.error("广播消息失败，sessionId: {}", session.getId(), e);
                }
            }
        });
    }
    
    /**
     * ✅ 启动定时广播任务
     * 这是演示服务端如何主动推送的关键！
     */
//    private void startBroadcastTask() {
//        // 每1秒执行一次
//        scheduler.scheduleAtFixedRate(() -> {
//            if (!sessions.isEmpty()) {
//                String message = "Hello World - " + System.currentTimeMillis();
//                broadcast(message);
//            }
//        }, 1, 30, TimeUnit.SECONDS);  // 初始延迟1秒，间隔1秒
//
//        log.info("已启动定时广播任务，每三十秒推送一次Hello World");
//    }
    
    /**
     * 获取当前连接数
     */
    public int getActiveConnections() {
        return sessions.size();
    }
}