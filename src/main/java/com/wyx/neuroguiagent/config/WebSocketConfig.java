// WebSocketConfig.java
package com.wyx.neuroguiagent.config;

import com.wyx.neuroguiagent.handler.MyWebSocketHandler;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;
import org.springframework.web.socket.server.standard.ServletServerContainerFactoryBean;

@Configuration
@Profile("!test")
@EnableWebSocket  // ✅ 关键：启用WebSocket支持
public class WebSocketConfig implements WebSocketConfigurer {
    
    private final MyWebSocketHandler myWebSocketHandler;
    
    // 通过构造函数注入Handler
    public WebSocketConfig(MyWebSocketHandler myWebSocketHandler) {
        this.myWebSocketHandler = myWebSocketHandler;
    }
    
    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        // 注册WebSocket处理器
        registry.addHandler(myWebSocketHandler, "/ws")
                .setAllowedOriginPatterns("*");  // 允许所有来源（生产环境要限制）
        
        // 如果要支持浏览器不支持WebSocket的情况，可以添加SockJS支持
        // registry.addHandler(myWebSocketHandler, "/ws").withSockJS();
    }

    @Bean
    public ServletServerContainerFactoryBean createWebSocketContainer() {
        ServletServerContainerFactoryBean container = new ServletServerContainerFactoryBean();
        // 设置文本消息的最大缓冲区（10MB）
        container.setMaxTextMessageBufferSize(10 * 1024 * 1024);
        // 设置二进制消息的最大缓冲区（10MB）
        container.setMaxBinaryMessageBufferSize(10 * 1024 * 1024);
        return container;
    }
}