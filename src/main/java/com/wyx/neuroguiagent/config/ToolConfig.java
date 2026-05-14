package com.wyx.neuroguiagent.config;

import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.tool.ToolCallback;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.Map;

@Slf4j
@Configuration
public class ToolConfig {

    @Autowired
    private ApplicationContext applicationContext;


//    @Bean
//    public ToolCallback[] guiTools() {
//        Map<String, ToolCallback> allToolCallbacks = applicationContext.getBeansOfType(ToolCallback.class);
//        for (Map.Entry<String, ToolCallback> stringToolCallbackEntry : allToolCallbacks.entrySet()) {
//            log.info("key: {}" , stringToolCallbackEntry.getKey());
//            ToolCallback value = stringToolCallbackEntry.getValue();
//            log.info("value:{}",value.getToolDefinition());
//        }
//        return allToolCallbacks.values().toArray(new ToolCallback[0]);
//    }
}
