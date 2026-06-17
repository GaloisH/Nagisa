package com.wyx.neuroguiagent;

import org.springframework.ai.autoconfigure.openai.OpenAiAutoConfiguration;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration;

@SpringBootApplication(exclude = { OpenAiAutoConfiguration.class })
public class NeuroGuiAgentApplication {

    public static void main(String[] args) {
        SpringApplication.run(NeuroGuiAgentApplication.class, args);
    }

}
