package com.wyx.neuroguiagent.agent;


import cn.hutool.core.util.StrUtil;
import com.wyx.neuroguiagent.common.Action;
import com.wyx.neuroguiagent.handler.MyWebSocketHandler;
import com.wyx.neuroguiagent.utils.ImageSaveUtil;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.slf4j.MDC;
import org.springframework.ai.chat.messages.*;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.chat.model.ToolContext;
import org.springframework.ai.chat.prompt.ChatOptions;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.ai.model.Media;
import org.springframework.ai.openai.OpenAiChatOptions;
import org.springframework.ai.tool.ToolCallback;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.stereotype.Component;
import org.springframework.util.MimeTypeUtils;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;

import java.io.IOException;
import java.util.*;

@Slf4j
@Component
public class GuiAgent {

    public static final String system_prompt = """
        # Role
        You are an intelligent GUI Agent capable of performing multi-step tasks on a computer. 
        You control the mouse and keyboard to achieve the user's high-level goals.
        
        # Operational Space
        - The screen coordinates are normalized to a 1000x1000 grid. 
        - Top-left is (0,0), Bottom-right is (1000,1000).
        - When you output coordinates for tools, use this 0-1000 scale. The system will automatically convert them to actual pixels.
        
        # Workflow (ReAct Loop)
        1. **Observe**: Analyze the provided screenshot.
        2. **Reason**: 
           - Check if the user's goal is achieved.
           - If achieved, simply reply with a final text summary (do not call tools).
           - If not achieved, determine the NEXT single atomic action required.
        3. **Act**: Call the appropriate tool.
        4. **Wait**: The system will execute the tool and provide you with a new screenshot in the next turn.
        
        # Rules
        - **One Step at a Time**: Only call ONE tool per turn unless typing requires a click first.
        - **Visual Grounding**: Look carefully at the UI elements. If you need to click an icon, estimate its center in the 1000x1000 grid.
        - **Finish Condition**: When the task is done, output a text response telling the user it is complete. DO NOT call a tool if the task is done.
        - **Retry**: If a step fails (e.g., menu didn't open), analyze the new screenshot and try a corrected action.
    """;

    @Resource
    private ToolCallback[] guiTools;

    private static HashMap<String,ToolCallback> toolMap = new HashMap<>();

    @PostConstruct
    public void init() {
        for (ToolCallback mouseTool : guiTools) {
            toolMap.put(mouseTool.getName(), mouseTool);
        }
    }

    @Resource
    private ChatModel geminiVisualModel;


    public String runTask(String message, WebSocketSession session) {
        // 0.工具上下文配置
        ToolContext toolContext = new ToolContext(Map.of("session",session));

        // 1.初始化对话历史
        log.info("开始运行agent loop, sessionId {}, UserInputMessage {}", session.getId(), message);
        List<Message> historyMessages = new ArrayList<>();
        historyMessages.add(new SystemMessage(system_prompt));
        historyMessages.add(new UserMessage("Goal: " + message + ". Please start by observing the screen."));

        // 2.agent 循环
        int stepCount = 0;
        int maxSteps = 15;
        while (stepCount < maxSteps) {
            stepCount++;
            log.info("Step {}, task {}, sessionId {}",stepCount,message,session.getId());
            // 2.1 构建当前轮次 UserMessage ，包括：请求客户端当前截图并保存至本地，截图作为UserMessage一部分
            long screenShotStartTime = System.currentTimeMillis();
            String jpegPictureBase64 = MyWebSocketHandler.sendRequestAndWait(session, "",
                    Collections.singletonList(new Action("SCREENSHOT", Map.of())));
            log.info("轮次{}, 截图请求耗时 {} ms", stepCount,  System.currentTimeMillis() - screenShotStartTime);
            String savePath = ImageSaveUtil.saveBase64ImageAsJpeg(jpegPictureBase64);
            log.info(savePath == null ? "截图保存失败" : ("截图已保存至" + savePath));
            byte[] imageBytes = Base64.getDecoder().decode(jpegPictureBase64);
            org.springframework.core.io.Resource imageResource = new ByteArrayResource(imageBytes);
            Media imageMedia = new Media(MimeTypeUtils.IMAGE_JPEG, imageResource);
            UserMessage userMessage = new UserMessage(
                    "Here is the current screen state. What should we do next?",
                    List.of(imageMedia));

            // 2.2 加入完UserMessage之后，call LLM
            // 关键点：为避免消息体积线性膨胀，历史消息中不应包含前几轮循环的客户端截图。
            // 因此，我们在发送给LLM时构造一个list包含当前这一轮的截图，但调用完成后仅将UserMessage的文本部分加入历史消息
            ArrayList<Message> sendMessages = new ArrayList<>(historyMessages);
            sendMessages.add(userMessage);
            long startLLMInvoke = System.currentTimeMillis();
            ChatResponse response = geminiVisualModel.call(new Prompt(sendMessages,
                    OpenAiChatOptions.builder().toolCallbacks(guiTools).build()));
            log.info("轮次{}, LLM call 耗时 {} ms", stepCount,  System.currentTimeMillis() - startLLMInvoke);
            historyMessages.add(new UserMessage("[Image of screen state]"));

            // 2.3 解析LLM返回的assistantMessage是否包括工具调用，若没有则LLM认为任务已完成，直接返回
            AssistantMessage assistantMessage = response.getResult().getOutput();
            historyMessages.add(assistantMessage);
            if (!assistantMessage.hasToolCalls()){
                log.info("任务已完成，sessionId {},轮次 {}", session.getId(), stepCount);
                return assistantMessage.getText();
            }

            // 2.4 如果包括工具调用，说明任务仍然要继续执行
            // 2.4.1 首先将AssistantMessage的内容返回给客户端，如果没有内容则返回默认内容
            log.info("[Response AssistantMessage] sessionId: {} | content: {} | token: {}",
                    session.getId(), assistantMessage.getText(), response.getMetadata().getUsage());
//            String sendMessage = StrUtil.isBlank(assistantMessage.getText()) ? "正在为您处理" : assistantMessage.getText();
            boolean isSendSuccess = MyWebSocketHandler.sendResponse(session, "");
            if (!isSendSuccess){
                log.error("Assistant Message 发送失败，sessionId {}",session.getId());
            }

            // 2.4.2 顺序执行工具调用，结果加入List<ToolResponse>，用 List<ToolResponse> 构造ToolResponseMessage
            List<AssistantMessage.ToolCall> toolCalls = assistantMessage.getToolCalls();
            List<ToolResponseMessage.ToolResponse> toolResponses = new ArrayList<>();
            long toolInvokeStart = System.currentTimeMillis();
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
            log.info("轮次{}, tool invoke 耗时 {} ms", stepCount,  System.currentTimeMillis() - toolInvokeStart);
            historyMessages.add(new ToolResponseMessage(toolResponses));

        }

        // 3.若循环达到最大步数则返回错误信息
        log.info("[WARN] Max steps reached, sessionId {}",session.getId());
        return "Task stopped due to max steps limit.";
    }

//    /**
//     * 根据输入命令执行桌面操作
//     * @param message
//     * @return
//     */
//    public String actWithTools(String message, WebSocketSession session) {
//        // 0.工具上下文配置
//        ToolContext toolContext = new ToolContext(Map.of("session",session));
//
//        // 1.将UserMessage加入历史消息列表发送给AI，等待第一轮回复，并将回复的 assistantMessage 直接发送给客户端
//        List<Message> historyMessages = new ArrayList<>();
//        historyMessages.add(new UserMessage(message));
//        ChatResponse response = geminiVisualModel.call(new Prompt(historyMessages));
//        AssistantMessage assistantMessage = response.getResult().getOutput();
//        log.info("[Response AssistantMessage] sessionId: {} | content: {} | token: {}",
//                    session.getId(), assistantMessage.getText(), response.getMetadata().getUsage());
//        if (StrUtil.isBlank(assistantMessage.getText())){
//            assistantMessage = new AssistantMessage("正在为您处理...");
//            log.info("调整 assistantMessage 为默认内容");
//        }
//        historyMessages.add(assistantMessage);
//        boolean isSendSuccess = MyWebSocketHandler.sendResponse(session, assistantMessage.getText());
//        if (!isSendSuccess){
//            log.error("Assistant Message 发送失败，sessionId {}, 消息内容{}",session.getId(),assistantMessage.getText());
//        }
//
//        // 2.如果AI觉得有工具需要调用，则解析工具调用并执行
//        if (response.hasToolCalls()){
//            List<AssistantMessage.ToolCall> toolCalls = response.getResult().getOutput().getToolCalls();
//            List<ToolResponseMessage.ToolResponse> toolResponses = new ArrayList<>();
//            // 如果有多个工具调用则依次解析，最终所有工具结果加入到 toolResponses 中
//            for (AssistantMessage.ToolCall toolCall : toolCalls) {
//                // 解析工具调用信息
//                String toolName = toolCall.name();
//                String rawArgs = toolCall.arguments();
//                String callId = toolCall.id();
//                log.info("[ACTION] sessionId: {} | Call: {} | Args (Normalized): {}",session.getId(), toolName, rawArgs);
//
//                // 查找并执行工具（toolMap为预先定义的工具名称-函数映射）
//                String toolOutput = "Error: Tool not found";
//                ToolCallback toolCallback = toolMap.get(toolName);
//                if (toolCallback != null) {
//                    try {
//                        toolOutput = toolCallback.call(rawArgs,toolContext);
//                    } catch (Exception e) {
//                        toolOutput = "Error executing tool: " + e.getMessage();
//                    }
//                }
//                log.info("[OBSERVATION] Result: {}", toolOutput);
//
//                // 得到结果
//                toolResponses.add(new ToolResponseMessage.ToolResponse(callId, toolName, toolOutput));
//            }
//            // 该轮次所有工具调用结果封装成ToolResponseMessage加入历史消息
//            historyMessages.add(new ToolResponseMessage(toolResponses));
//        }
//
//        ChatResponse finalResponse = geminiVisualModel.call(new Prompt(historyMessages));
//        log.info("[Response AssistantMessage] sessionId: {} | content: {} | token: {}",
//                session.getId(), finalResponse.getResult().getOutput().getText(), finalResponse.getMetadata().getUsage());
//        return finalResponse.getResult().getOutput().getText();
//    }
}
