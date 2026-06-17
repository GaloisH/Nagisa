package com.wyx.neuroguiagent.utils;

import org.springframework.ai.chat.messages.AssistantMessage;

import java.util.List;

public class ToolCallUtils {

    public static String toolCallsToJsonArray(List<AssistantMessage.ToolCall> toolCalls) {
        if (toolCalls == null || toolCalls.isEmpty()) {
            return "[]";
        }

        StringBuilder sb = new StringBuilder();
        sb.append("[");

        for (int i = 0; i < toolCalls.size(); i++) {
            AssistantMessage.ToolCall t = toolCalls.get(i);
            sb.append("{")
              .append("\"id\":").append(toJsonString(t.id())).append(",")
              .append("\"type\":").append(toJsonString(t.type())).append(",")
              .append("\"name\":").append(toJsonString(t.name())).append(",")
              .append("\"arguments\":").append(toJsonString(t.arguments()))
              .append("}");

            if (i < toolCalls.size() - 1) {
                sb.append(",");
            }
        }

        sb.append("]");
        return sb.toString();
    }

    /** 简单 JSON 字符串转义（双引号和反斜杠） */
    private static String toJsonString(String value) {
        if (value == null) {
            return "null";
        }
        String escaped = value.replace("\\", "\\\\").replace("\"", "\\\"");
        return "\"" + escaped + "\"";
    }

    // 你的 record

}