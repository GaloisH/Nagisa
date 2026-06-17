package com.wyx.neuroguiagent.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Data
@Component
@ConfigurationProperties(prefix = "app.ai")
public class AiApiProperties {

    private ModelConfig deepseek = new ModelConfig();
    private ModelConfig gemini = new ModelConfig();

    @Data
    public static class ModelConfig {
        private String apiKey = "";
        private String baseUrl = "";
        private String model = "";
    }
}
