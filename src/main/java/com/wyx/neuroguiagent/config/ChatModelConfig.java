package com.wyx.neuroguiagent.config;

import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.ai.openai.OpenAiChatModel;
import org.springframework.ai.openai.OpenAiChatOptions;
import org.springframework.ai.openai.api.OpenAiApi;
import org.springframework.ai.tool.ToolCallback;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.ClientHttpRequestInterceptor;
import org.springframework.http.client.ClientHttpResponse;
import org.springframework.web.client.RestClient;

import java.nio.charset.StandardCharsets;

@Slf4j
@Configuration
public class ChatModelConfig {


    public RestClient.Builder getRestClientBuilder() {
        // 配置一个http拦截器更好地看到input schema
        ClientHttpRequestInterceptor loggingInterceptor = (request, body, execution) -> {
            // 这里的 body 就是经过 Spring AI 处理后，最终发给大模型的原生 JSON 字符串
            String rawJsonPayload = new String(body, StandardCharsets.UTF_8);
//            System.out.println(rawJsonPayload);
//            log.info("Raw JSON Payload: {}", rawJsonPayload);
            ClientHttpResponse response = execution.execute(request, body);
//            log.info(JSONUtil.toJsonStr(response));
            return response;
        };

        // 2. 将拦截器配置到 RestClient.Builder 中
        return RestClient.builder()
                .requestInterceptor(loggingInterceptor);
    }


    /**
     * gemini 中转站 api，采用类 open-ai 模型调用方式，用的是 openAi 的包，
     * 核心是 base_url，api-key和模型名称，以及其他一些模型可选项，如温度
     * @return gemini 视觉模型
     */
    @Bean
    public ChatModel geminiVisualModel(){

        OpenAiApi api = OpenAiApi.builder()
                .apiKey("sk-P6buRuIVYws3TS0XbCoh9U2ygvKD8dgHHVX0DYnFyHSMudtV")
                .baseUrl("https://jeniya.top/")
                .restClientBuilder(getRestClientBuilder()) // 关键点：注入带日志拦截的底层客户端
                .build();
        OpenAiChatOptions chatOptions = OpenAiChatOptions.builder()
                .model("gemini-3-flash-preview")
                .temperature(0.1)
                .internalToolExecutionEnabled(false)
                .build();

        return OpenAiChatModel.builder()
                .openAiApi(api)
                .defaultOptions(chatOptions)
                .build();

    }


    @Bean
    public ChatModel deepSeekChatModel(){

        ClientHttpRequestInterceptor loggingInterceptor = (request, body, execution) -> {
            // 1. 把字节数组转成字符串
            String requestBody = new String(body, StandardCharsets.UTF_8);
            // 2. 使用 Hutool 解析成 JSON 对象
            JSONObject json = JSONUtil.parseObj(requestBody);
            // 3. 注入 thinking 参数 (相当于在 JSON 根部加了 "thinking": {"type": "disabled"})
//            // DeepSeek 官方文档要求：如果要关闭思考模式，就这样设置
//            JSONObject thinkingNode = new JSONObject();
//            thinkingNode.set("type", "disabled");
//            json.set("thinking", thinkingNode);
            // 4. 转回字节数组并继续执行请求
            byte[] modifiedBody = json.toString().getBytes(StandardCharsets.UTF_8);
            return execution.execute(request, modifiedBody);
        };



        // toolcallback工厂模式
        OpenAiApi api = OpenAiApi.builder()
                .apiKey("sk-101be397b9b54d118e1dce4258adc3a5")
                .baseUrl("https://api.deepseek.com")
                .restClientBuilder(RestClient.builder().requestInterceptor(loggingInterceptor)) // 关键点：注入带日志拦截的底层客户端
                .build();
        OpenAiChatOptions chatOptions = OpenAiChatOptions.builder()
                .model("deepseek-v4-flash")
                .temperature(0.1)
                .internalToolExecutionEnabled(false)
                .build();

        return OpenAiChatModel.builder()
                .openAiApi(api)
                .defaultOptions(chatOptions)
                .build();

    }

    @Bean
    public ChatModel geminiChatModel(){

        // toolcallback工厂模式
        OpenAiApi api = OpenAiApi.builder()
                .apiKey("sk-P6buRuIVYws3TS0XbCoh9U2ygvKD8dgHHVX0DYnFyHSMudtV")
                .baseUrl("https://jeniya.top/")
                .restClientBuilder(getRestClientBuilder()) // 关键点：注入带日志拦截的底层客户端
                .build();
        OpenAiChatOptions chatOptions = OpenAiChatOptions.builder()
                .model("gemini-3-flash-preview")
                .temperature(0.1)
                .internalToolExecutionEnabled(false)
                .build();

        return OpenAiChatModel.builder()
                .openAiApi(api)
                .defaultOptions(chatOptions)
                .build();

    }


    @Bean
    public ChatModel geminiExtractGoalModel(){

        // toolcallback工厂模式
        OpenAiApi api = OpenAiApi.builder()
                .apiKey("sk-P6buRuIVYws3TS0XbCoh9U2ygvKD8dgHHVX0DYnFyHSMudtV")
                .baseUrl("https://jeniya.top/")
                .restClientBuilder(getRestClientBuilder()) // 关键点：注入带日志拦截的底层客户端
                .build();
        OpenAiChatOptions chatOptions = OpenAiChatOptions.builder()
                .model("gemini-3-flash-preview")
                .temperature(0.1)
                .internalToolExecutionEnabled(false)
                .build();

        return OpenAiChatModel.builder()
                .openAiApi(api)
                .defaultOptions(chatOptions)
                .build();

    }






}
