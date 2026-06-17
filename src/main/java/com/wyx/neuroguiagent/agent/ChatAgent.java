package com.wyx.neuroguiagent.agent;

import cn.hutool.core.util.StrUtil;
import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;
import com.wyx.neuroguiagent.handler.MyWebSocketHandler;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.chat.messages.Message;
import org.springframework.ai.chat.messages.ToolResponseMessage;
import org.springframework.ai.chat.messages.UserMessage;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.chat.model.ToolContext;
import org.springframework.ai.chat.prompt.ChatOptions;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.ai.openai.OpenAiChatOptions;
import org.springframework.ai.tool.ToolCallback;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.WebSocketSession;
import reactor.core.publisher.Flux;

import java.util.*;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

@Slf4j
@Component
public class ChatAgent {

    @Resource
    private ChatModel geminiChatModel;

    @Resource
    private ChatModel deepSeekChatModel;


    @Resource
    private ToolCallback[] chatAgentTools;

    private static HashMap<String,ToolCallback> toolMap = new HashMap<>();

    @PostConstruct
    public void init() {
        for (ToolCallback mouseTool : chatAgentTools) {
            toolMap.put(mouseTool.getName(), mouseTool);
        }
    }



    public void runTask(String userInput, WebSocketSession session) {

        ToolContext toolContext = new ToolContext(Map.of(
                "session", session,
                "currentMessages", Collections.singletonList(new UserMessage(userInput))
        ));
        // 1.call AI，然后发送 stream chunk 给客户端, sendStreamResponse 是注册一个回调然后立即返回
        List<Message> historyMessages = new ArrayList<>();
        historyMessages.add(new UserMessage(userInput));
        Flux<ChatResponse> response = deepSeekChatModel.stream(new Prompt(historyMessages,
                OpenAiChatOptions.builder().toolCallbacks(chatAgentTools).build()));
        Future<AssistantMessage> assistantMessageFuture = MyWebSocketHandler.sendStreamResponse(session, response);

        // 2.等待流式消息传输完毕后拿到完整消息，如果没有工具调用则说明任务完成
        AssistantMessage assistantMessage = null;
        try {
            assistantMessage = assistantMessageFuture.get(120, TimeUnit.SECONDS);
        } catch (TimeoutException e) {
            log.error("stream subscribe 回调执行超时", e);
            return;
        } catch (Exception e){
            log.error("assistantMessageFuture get 失败", e);
            return;
        }
        if (!assistantMessage.hasToolCalls()){
            log.info("任务执行完毕");
            return;
        }

        // 3. 如果有工具调用则执行工具调用并执行下一轮AI call
        historyMessages.add(assistantMessage);
        List<AssistantMessage.ToolCall> toolCalls = assistantMessage.getToolCalls();
        List<ToolResponseMessage.ToolResponse> toolResponses = new ArrayList<>();
        for (AssistantMessage.ToolCall toolCall : toolCalls) {
            // 解析工具调用信息
            String toolName = toolCall.name();
            String rawArgs = toolCall.arguments();
            String callId = toolCall.id();
            log.info("[ACTION] sessionId: {} | Call: {} | Args (Normalized): {}",session.getId(), toolName, rawArgs);
            // 查找并执行工具（toolMap为预先定义的工具名称-函数映射）
            ToolCallback toolCallback = toolMap.get(toolName);
            String toolOutput = toolCallback == null ? "Error: Tool not found" : toolCallback.call(rawArgs,toolContext);
            log.info("[OBSERVATION] Result: {}", toolOutput);
            toolResponses.add(new ToolResponseMessage.ToolResponse(callId, toolName, toolOutput));
        }
        historyMessages.add(new ToolResponseMessage(toolResponses));
        historyMessages.add(new UserMessage("tool Response is above"));
        Flux<ChatResponse> response2 = deepSeekChatModel.stream(
                new Prompt(
                        historyMessages,
                        OpenAiChatOptions.builder().toolCallbacks(chatAgentTools).build()
                )
        );

        // todo 这里假设最多两轮，后续可改循环
        assistantMessageFuture = MyWebSocketHandler.sendStreamResponse(session, response2);
        try {
            assistantMessage = assistantMessageFuture.get(120, TimeUnit.SECONDS);
        } catch (TimeoutException e) {
            log.error("stream subscribe 回调执行超时", e);
            return;
        } catch (Exception e){
            log.error("assistantMessageFuture get 失败", e);
            return;
        }
        log.info("任务执行完毕，最终回复：{}",assistantMessage.getText());
    }


    private AssistantMessage getEntireMessageFromChunks(List<ChatResponse> chunks) {
        StringBuilder fullText = new StringBuilder();
        List<AssistantMessage.ToolCall> toolCallsList = new ArrayList<>();
        for (ChatResponse chunk : chunks) {
            AssistantMessage chunkMsg = chunk.getResult().getOutput();
            if (StrUtil.isNotBlank(chunkMsg.getText())) {
                fullText.append(chunkMsg.getText());
            }
            if (chunkMsg.hasToolCalls()) {
                toolCallsList.addAll(chunkMsg.getToolCalls());
            }
        }
        return new AssistantMessage(fullText.toString(), Map.of(), toolCallsList);
    }



    // 把assistantMessage里的context字段去掉
    private AssistantMessage toCleanAssistantMessage(AssistantMessage assistantMessage) {
        List<AssistantMessage.ToolCall> rawToolCalls = assistantMessage.getToolCalls();
        List<AssistantMessage.ToolCall> cleanToolCalls = new ArrayList<>();

        for (AssistantMessage.ToolCall call : rawToolCalls) {
            JSONObject argsJson = JSONUtil.parseObj(call.arguments());

            argsJson.remove("toolContext"); // 擦除“作弊”痕迹
            String cleanArgsStr = argsJson.toString();

            cleanToolCalls.add(new AssistantMessage.ToolCall(
                    call.id(),
                    call.type(),
                    call.name(),
                    cleanArgsStr // 这里的 JSON 现在只有 {"guiTaskGoal": "..."}
            ));
        }
        return new AssistantMessage(
                assistantMessage.getText(), // 保留文本回复
                assistantMessage.getMetadata(),    // 保留元数据
                cleanToolCalls                     // 替换为洗白后的工具调用
        );

    }


}
