package com.wyx.neuroguiagent.config;

import com.wyx.neuroguiagent.tools.ChatAgentToolClass;
import com.wyx.neuroguiagent.tools.GUIToolClass;
import lombok.extern.slf4j.Slf4j;
import org.springframework.ai.tool.ToolCallback;
import org.springframework.ai.tool.ToolCallbacks;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Slf4j
@Configuration
public class ToolConfig {

    @Bean
    public ToolCallback[] chatAgentTools(ChatAgentToolClass chatAgentTools) {
        ToolCallback[] toolCallbacks = ToolCallbacks.from(chatAgentTools);
        return toolCallbacks;
    }

    @Bean
    public ToolCallback[] guiTools(GUIToolClass guiTools) {
        ToolCallback[] toolCallbacks = ToolCallbacks.from(guiTools);
        return toolCallbacks;
    }


}
