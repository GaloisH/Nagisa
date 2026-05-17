package com.wyx.neuroguiagent.common;


/**
 * 同一个 Websocket 连接可能
 */
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.ai.chat.model.ChatModel;

import java.util.ArrayList;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class BaseResponse {

    private String type;        // 类型，这里暂时分成默认，即完整消息，和"stream"，流式响应
    private int code;           // 状态码，如 200, 404, 500
    private String message;     // 状态描述，如 "OK", "Internal Error"
    private Object content;     // AI 的回应内容或普通文本内容内容
    private String callId;     //标识请求
    private List<Action> actions; // 指令数组，可以要求客户端执行多个动作
    private Boolean end;     // 如果是流式响应，该字段标识流是否结束

    /**
     * 快捷成功响应：仅文本
     */
    public static BaseResponse success(String content) {
        return BaseResponse.builder()
                .code(200)
                .message("OK")
                .content(content)
                .callId("")
                .actions(new ArrayList<>())
                .build();
    }

    /**
     * 快捷成功响应：带动作
     */
    public static BaseResponse success(String content,String callId, List<Action> actions) {
        return BaseResponse.builder()
                .code(200)
                .message("OK")
                .content(content)
                .callId(callId)
                .actions(actions)
                .build();
    }

    /**
     * 快捷成功响应：单一动作
     */
    public static BaseResponse successWithAction(String content, String callId,Action action) {
        return BaseResponse.builder()
                .code(200)
                .message("OK")
                .content(content)
                .callId(callId)
                .actions(List.of(action))
                .build();
    }

    /**
     * 快捷错误响应
     */
    public static BaseResponse error(int code, String message) {
        return BaseResponse.builder()
                .code(code)
                .message(message)
                .content(null)
                .callId("")
                .actions(null)
                .build();
    }

    /**
     * 默认服务器错误
     */
    public static BaseResponse fatal() {
        return error(500, "Internal Server Error");
    }

    // 辅助方法：向现有响应添加 Action
    public void addAction(Action action) {
        if (this.actions == null) {
            this.actions = new ArrayList<>();
        }
        this.actions.add(action);
    }
}
