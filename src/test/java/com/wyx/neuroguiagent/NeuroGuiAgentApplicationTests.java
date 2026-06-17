package com.wyx.neuroguiagent;

import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONUtil;
import com.wyx.neuroguiagent.agent.ChatAgent;
import com.wyx.neuroguiagent.agent.GuiAgent;
import com.wyx.neuroguiagent.utils.ToolCallUtils;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.ai.openai.OpenAiChatOptions;
import org.springframework.ai.tool.ToolCallback;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.HttpHeaders;
import org.springframework.test.annotation.Repeat;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.WebSocketExtension;
import org.springframework.web.socket.WebSocketMessage;
import org.springframework.web.socket.WebSocketSession;
import reactor.core.publisher.Flux;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.URI;
import java.security.Principal;
import java.util.List;
import java.util.Map;

@Slf4j
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class NeuroGuiAgentApplicationTests {

    @Resource
    private ChatAgent chatAgent;

    @Resource
    private ChatModel deepSeekChatModel;

    @Resource
    private ChatModel geminiVisualModel;

    @Resource
    private ToolCallback[] chatAgentTools;


    @Test
    void testDeepSeekChatModel() throws InterruptedException {

//        long start = System.currentTimeMillis();
//        Flux<ChatResponse> chatResponseFlux = geminiVisualModel.stream((new Prompt("帮我写一篇1000字作文，题目，止战之殇",
//                OpenAiChatOptions.builder().toolCallbacks(chatAgentTools).build())));
//        List<ChatResponse> chunks = chatResponseFlux
//                .collectList()
//                .block();
//        System.out.println(System.currentTimeMillis() - start);
//        Assertions.assertNotNull(chunks);
//        for (int i  = 0; i < chunks.size(); i++) {
//            ChatResponse chunk = chunks.get(i);
//            System.out.println("=== chunk" + (i+1) + " start ===");
//            System.out.println("metadata: " + chunk.getMetadata());
//            System.out.println("text: " + chunk.getResult().getOutput().getText());
//            List<AssistantMessage.ToolCall> toolCalls = chunk.getResult().getOutput().getToolCalls();
//            String json = ToolCallUtils.toolCallsToJsonArray(toolCalls);
//            System.out.println("toolCall: " + json);
//        }
//
//
//        start = System.currentTimeMillis();
//        ChatResponse response = geminiVisualModel.call(new Prompt("你是谁",
//                OpenAiChatOptions.builder().toolCallbacks(chatAgentTools).build()));
//        System.out.println(System.currentTimeMillis() - start);
//        System.out.println(response.getResult().getOutput().getText());

//        long costAICall = 0;
//        long costAIStream = 0;
//        int turnNum = 50;
//        for (int i = 0; i < turnNum; i++) {
//            long start1 = System.currentTimeMillis();
//            ChatResponse response = geminiVisualModel.call(new Prompt("帮我打开浏览器",
//                    OpenAiChatOptions.builder().toolCallbacks(chatAgentTools).build()));
//            long end1 = System.currentTimeMillis();
//            costAICall += end1 - start1;
//            System.out.println("第" + (i+1) + "轮，AI call 耗时" + (end1 - start1) + "ms");
//
//
//            long start2 = System.currentTimeMillis();
//            Flux<ChatResponse> chatResponseFlux = geminiVisualModel.stream((new Prompt("帮我打开浏览器",
//                    OpenAiChatOptions.builder().toolCallbacks(chatAgentTools).build())));
//            List<ChatResponse> chunks = chatResponseFlux
//                    .collectList()
//                    .block();
//            long end2 = System.currentTimeMillis();
//            costAIStream += end2 - start2;
//            System.out.println("第" + (i+1) + "轮，AI stream 耗时" + (end2 - start2) + "ms");
//        }
//
//        System.out.println("costAICall " + costAICall + "ms");
//        System.out.println("costAIStream " + costAIStream + "ms");


        Flux<ChatResponse> chatResponseFlux = deepSeekChatModel.stream((new Prompt("帮我打开浏览器",
                OpenAiChatOptions.builder().toolCallbacks(chatAgentTools).build())));
//        long start2 = System.currentTimeMillis();
        chatResponseFlux.index().subscribe(

                chunk -> {
                    Long i = chunk.getT1();
                    ChatResponse response = chunk.getT2();
                    log.info("=== chunk{} start ===", i + 1);
                    System.out.println("metadata: " + response.getMetadata());
                    System.out.println("text: " + response.getResult().getOutput().getText());
                    List<AssistantMessage.ToolCall> toolCalls = response.getResult().getOutput().getToolCalls();
                    String json = ToolCallUtils.toolCallsToJsonArray(toolCalls);
                    System.out.println("toolCall: " + json);
                },

                error -> {},

                () -> {



                }
        );
//
        Thread.sleep(1000*1000);
    }


    @Test
    void contextLoads() {
//        System.out.println(guiAgent.actWithTools("帮我点击桌面的(500,500)坐标", new WebSocketSession() {
//            @Override
//            public String getId() {
//                return "";
//            }
//
//            @Override
//            public URI getUri() {
//                return null;
//            }
//
//            @Override
//            public HttpHeaders getHandshakeHeaders() {
//                return null;
//            }
//
//            @Override
//            public Map<String, Object> getAttributes() {
//                return Map.of();
//            }
//
//            @Override
//            public Principal getPrincipal() {
//                return null;
//            }
//
//            @Override
//            public InetSocketAddress getLocalAddress() {
//                return null;
//            }
//
//            @Override
//            public InetSocketAddress getRemoteAddress() {
//                return null;
//            }
//
//            @Override
//            public String getAcceptedProtocol() {
//                return "";
//            }
//
//            @Override
//            public void setTextMessageSizeLimit(int messageSizeLimit) {
//
//            }
//
//            @Override
//            public int getTextMessageSizeLimit() {
//                return 0;
//            }
//
//            @Override
//            public void setBinaryMessageSizeLimit(int messageSizeLimit) {
//
//            }
//
//            @Override
//            public int getBinaryMessageSizeLimit() {
//                return 0;
//            }
//
//            @Override
//            public List<WebSocketExtension> getExtensions() {
//                return List.of();
//            }
//
//            @Override
//            public void sendMessage(WebSocketMessage<?> message) throws IOException {
//
//            }
//
//            @Override
//            public boolean isOpen() {
//                return true;
//            }
//
//            @Override
//            public void close() throws IOException {
//
//            }
//
//            @Override
//            public void close(CloseStatus status) throws IOException {
//
//            }
//        }));
    }

}
