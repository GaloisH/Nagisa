package com.wyx.neuroguiagent;

import com.wyx.neuroguiagent.agent.ChatAgent;
import com.wyx.neuroguiagent.agent.GuiAgent;
import jakarta.annotation.Resource;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.HttpHeaders;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.WebSocketExtension;
import org.springframework.web.socket.WebSocketMessage;
import org.springframework.web.socket.WebSocketSession;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.URI;
import java.security.Principal;
import java.util.List;
import java.util.Map;


@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class NeuroGuiAgentApplicationTests {

    @Resource
    private ChatAgent chatAgent;

//    @Test
//    void testDeepSeekChatModel(){
//        System.out.println(chatAgent.runTask("你是谁"));
//    }


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
