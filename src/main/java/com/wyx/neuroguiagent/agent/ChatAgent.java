package com.wyx.neuroguiagent.agent;

import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Flux;

@Slf4j
@Component
public class ChatAgent {

    @Resource
    private ChatModel deepSeekChatModel;

    public String runTask(String userInput){
        return deepSeekChatModel.call(userInput);
    }
}
