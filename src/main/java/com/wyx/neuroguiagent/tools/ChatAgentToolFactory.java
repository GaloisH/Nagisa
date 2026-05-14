package com.wyx.neuroguiagent.tools;

import com.wyx.neuroguiagent.agent.ChatAgent;
import com.wyx.neuroguiagent.agent.GuiAgent;
import com.wyx.neuroguiagent.handler.MyWebSocketHandler;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.ai.chat.model.ToolContext;
import org.springframework.ai.tool.ToolCallback;
import org.springframework.ai.tool.ToolCallbacks;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.WebSocketSession;

import java.util.Map;
import java.util.concurrent.*;

@Slf4j
@Configuration
public class ChatAgentToolFactory implements ToolFactory {

    @Resource
    private ChatAgent chatAgent;

    @Resource
    private GuiAgent guiAgent;

    private final ExecutorService agentExecutor = new ThreadPoolExecutor(
            10, 50, 60L, TimeUnit.SECONDS, new LinkedBlockingQueue<>(1000));


    @Tool(description = "Click on a specified position on the screen (x, y). Coordinates are normalized (0-1000).")
    public String callGuiAgent(@ToolParam(description = "goal of guiTask to provide guiAgent") String guiTaskGoal,
                                ToolContext toolContext)  {
        Map<String, Object> context = toolContext.getContext();
        WebSocketSession session = (WebSocketSession)context.get("session");
        Runnable guiTask = () -> {
            // 这里真的有必要用历史消息加gui执行结果润色吗，我感觉直接让模型润色执行结果就可以了。
            String guiTaskResult = "很抱歉，您之前的" + guiTaskGoal + "的任务执行失败了，可以允许我重试一次吗" ;
            try {
                guiTaskResult = guiAgent.runTask(guiTaskGoal, session);
            } catch (Exception e) {
                log.error("guiTask执行失败，goal{}",guiTaskGoal,e);
            }
            MyWebSocketHandler.sendResponse(session,guiTaskResult);
        };
        agentExecutor.submit(guiTask);
        return "gui 任务成功启动，正在执行...";
    }

    @Override
    public String getDescription() {
        return "生产 chatAgent 所需的工具";
    }

    @Override
    public ToolCallback[] createTools() {
        return ToolCallbacks.from(new ChatAgentToolFactory());
    }

    @Bean
    public ToolCallback[] chatAgentTools() {
        return createTools();
    }
}
