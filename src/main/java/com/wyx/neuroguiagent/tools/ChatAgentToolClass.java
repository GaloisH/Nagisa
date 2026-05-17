package com.wyx.neuroguiagent.tools;

import com.wyx.neuroguiagent.agent.GuiAgent;
import com.wyx.neuroguiagent.handler.MyWebSocketHandler;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.ai.chat.messages.Message;
import org.springframework.ai.chat.messages.MessageType;
import org.springframework.ai.chat.messages.SystemMessage;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.chat.model.ToolContext;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.context.annotation.Configuration;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.WebSocketSession;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.*;

@Slf4j
@Component
public class ChatAgentToolClass {

    @Resource
    private ChatModel geminiExtractGoalModel;

    @Resource
    private GuiAgent guiAgent;

    private final ExecutorService agentExecutor = new ThreadPoolExecutor(
            10, 50, 60L, TimeUnit.SECONDS,
            new LinkedBlockingQueue<>(1000),
            new ThreadFactory() {
                private int count = 1;
                @Override
                public Thread newThread(Runnable r) {
                    return new Thread(r, "agent-thread-" + count++);
                }
            }
    );

    public static final String EXTRACT_GOAL_SYSTEM_PROMPT = """
            You are an extremely rational 'GUI Operation Instruction Extractor'.
            Within the current conversation context, the user has explicitly requested or implied the need for an action
            involving computer software, a webpage, or a screen interface.
            Your sole task is to read the conversation history, accurately extract the user's core operational intent,
            and convert it into a direct instruction executable by an automated program.
            [Strictly follow these output rules]:
            1. Coreference Resolution: You must resolve pronouns based on the context. For example, if the user says 'open it',
               you must identify whether 'it' refers to 'WeChat' or 'the browser' from previous messages, and output 'Open WeChat' or 'Open the browser'.
            2. Strict Formatting: Output exactly one concise imperative sentence. The format MUST be [Action + Target Object].
               Examples: 'Open NetEase Cloud Music', 'Search for tomorrow's weather in the browser', 'Close the current window'.
            3. Absolute Purification: Completely strip away all filler words (e.g., 'please', 'help me', 'could you'), 
               small talk, greetings, and role-play personas.
            4. Zero Redundancy: It is strictly forbidden to output any reasoning processes, prefixes 
               (e.g., 'The instruction is:', 'The user wants to:'), or explanatory text. 
               Your output will be read directly by code and must contain ONLY the final instruction.
    """;


    @Tool(description = """
        Invoke the local system GUI Agent to execute tasks that require interacting with the computer screen,
        graphical user interfaces (GUI), third-party software, or keyboard/mouse operations.
        You MUST call this tool when the user's request goes beyond pure text-based Q&A (e.g., 'open an app', 'click a button').
        [CRITICAL ASYNC BEHAVIOR]: This tool runs ASYNCHRONOUSLY in the background. Once invoked, it will immediately return a message
        indicating that the task has started. You MUST treat this "started" response as a COMPLETE SUCCESS.
        DO NOT call this tool repeatedly for the same user request. After calling, simply reply to the user naturally
        to inform them that you are processing their request.
    """)
    public String callGuiAgent(
            @ToolParam String goal,
            @ToolParam(required = false) ToolContext toolContext)  {
        Map<String, Object> context = toolContext.getContext();
        WebSocketSession session = (WebSocketSession)context.get("session");
        List<Message> currentMessages = (List<Message>)context.get("currentMessages");
        Runnable guiTask = () -> {
            // 考虑到只看当前轮次用户提问，需求可能模糊，将整个历史对话快照喂给大模型提炼需求
            String guiTaskGoal = extractGuiTaskGoal(currentMessages);
            log.info("sessionId:{}, extract Goal: {}", session.getId(), guiTaskGoal);
            // todo 返回值润色
            String guiTaskResult = "很抱歉，您之前的" + guiTaskGoal + "的任务执行失败了，可以允许我重试一次吗" ;
            try {
                guiTaskResult = guiAgent.runTask(guiTaskGoal, session);
            } catch (Exception e) {
                log.error("guiTask执行失败，goal{}",guiTaskGoal,e);
            }
            MyWebSocketHandler.sendResponse(session,guiTaskResult);
        };
        agentExecutor.submit(guiTask);
        return "successfully start the gui task";
    }

    public String extractGuiTaskGoal(List<Message> currentMessages){
        // 只留下非 systemPrompt 的消息
        // todo 只提取倒数第 3-5 条用户消息开始的截断历史，避免注意力涣散
        List<Message> messages = currentMessages.stream()
                .filter((message -> !message.getMessageType().equals(MessageType.SYSTEM)))
                .toList();
        messages = new ArrayList<>(messages);
        messages.addFirst(new SystemMessage(EXTRACT_GOAL_SYSTEM_PROMPT));
        Prompt prompt = new Prompt(messages);
        log.info("extract prompt: {}", prompt);
        return geminiExtractGoalModel.call(prompt).getResult().getOutput().getText();
    }


    public String getDescription() {
        return "生产 chatAgent 所需的工具";
    }



}
