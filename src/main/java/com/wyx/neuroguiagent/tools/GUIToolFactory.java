package com.wyx.neuroguiagent.tools;

import cn.hutool.core.util.StrUtil;
import com.wyx.neuroguiagent.common.Action;
import com.wyx.neuroguiagent.common.BaseResponse;
import com.wyx.neuroguiagent.handler.MyWebSocketHandler;
import jakarta.annotation.Nullable;
import lombok.extern.slf4j.Slf4j;
import org.springframework.ai.chat.model.ToolContext;
import org.springframework.ai.tool.ToolCallback;
import org.springframework.ai.tool.ToolCallbacks;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.WebSocketSession;

import java.util.Collections;
import java.util.Map;

@Slf4j
@Configuration
public class GUIToolFactory implements ToolFactory {

//    @Tool(description = "查询天气")
//    public String getWeatherOfBeiJing(@ToolParam String city,ToolContext toolContext) {
//        System.out.println(toolContext);
//        return toolContext == null ? "30度，阴" : "15度，晴";
//    }

    @Tool(description = "Click on a specified position on the screen (x, y). Coordinates are normalized (0-1000).")
    public String clickPosition(@ToolParam(description = "X coordinate (0-1000)") int x,
                                @ToolParam(description = "Y coordinate (0-1000)") int y,
                                ToolContext toolContext)  {
        double wait = 0.5; // fixed default wait
        if (toolContext == null || toolContext.getContext() == null
                || toolContext.getContext().isEmpty()) {
            log.error("ToolContext is null or empty, cannot click position");
            return "工具执行失败";
        }
        Map<String, Object> context = toolContext.getContext();
        WebSocketSession session = (WebSocketSession)context.get("session");
        Action action = new Action("click_position", Map.of("x", x, "y", y));
        String result = MyWebSocketHandler.sendRequestAndWait(session, "正在执行工具 click_position", Collections.singletonList(action));
        return StrUtil.isBlank(result) ? "工具执行失败" : String.format("Click command at (%d, %d) with wait %.2f", x, y, wait);
    }

    @Tool(description = "Double-click on a specified position on the screen (x, y).Coordinates are normalized (0-1000).")
    public String doubleClickPosition(
            @ToolParam(description = "X coordinate (0-1000)") int x,
            @ToolParam(description = "Y coordinate (0-1000)") int y,
            ToolContext toolContext) {
        double wait = 0.5;
        if (toolContext == null || toolContext.getContext() == null
                || toolContext.getContext().isEmpty()) {
            log.error("ToolContext is null or empty, cannot double click position");
            return "工具执行失败";
        }
        Map<String, Object> context = toolContext.getContext();
        WebSocketSession session = (WebSocketSession)context.get("session");
        Action action = new Action("double_click_position", Map.of("x", x, "y", y));
        String result = MyWebSocketHandler.sendRequestAndWait(session, "正在执行工具 double_click_position", Collections.singletonList(action));
        return StrUtil.isBlank(result) ? "工具执行失败" : String.format("Double click command at (%d, %d) with wait %.2f", x, y, wait);
    }

    @Tool(description = "Right-click on a specified position on the screen (x, y).Coordinates are normalized (0-1000).")
    public String rightClickPosition(
            @ToolParam(description = "X coordinate (0-1000)") int x,
            @ToolParam(description = "Y coordinate (0-1000)") int y,
            ToolContext toolContext) {
        double wait = 0.5;
        if (toolContext == null || toolContext.getContext() == null
                || toolContext.getContext().isEmpty()) {
            log.error("ToolContext is null or empty, cannot right click position");
            return "工具执行失败";
        }
        Map<String, Object> context = toolContext.getContext();
        WebSocketSession session = (WebSocketSession)context.get("session");
        Action action = new Action("right_click_position", Map.of("x", x, "y", y));
        String result = MyWebSocketHandler.sendRequestAndWait(session, "正在执行工具 right_click_position", Collections.singletonList(action));
        return StrUtil.isBlank(result) ? "工具执行失败" : String.format("Right click command at (%d, %d) with wait %.2f", x, y, wait);
    }

    @Tool(description = "Type text into the active input field.")
    public String typeText(
            @ToolParam(description = "Text to type") String text,
            @ToolParam(description = "Whether to press Enter after typing") boolean pressEnter,
            ToolContext toolContext) {
        double wait = 0.5;
        if (toolContext == null || toolContext.getContext() == null
                || toolContext.getContext().isEmpty()) {
            log.error("ToolContext is null or empty, cannot type text");
            return "工具执行失败";
        }
        Map<String, Object> context = toolContext.getContext();
        WebSocketSession session = (WebSocketSession)context.get("session");
        Action action = new Action("type_text", Map.of("text", text, "press_enter", pressEnter));
        String result = MyWebSocketHandler.sendRequestAndWait(session, "正在执行工具 type_text", Collections.singletonList(action));
        return StrUtil.isBlank(result) ? "工具执行失败" : String.format("Type text '%s' [Enter: %b] with wait %.2f", text, pressEnter, wait);
    }

    @Tool(description = "Scroll the mouse wheel. Positive value scrolls up, negative scrolls down.")
    public String scroll(
            @ToolParam(description = "Scroll units, positive for up, negative for down") int clicks,
            ToolContext toolContext
    ) {
        double wait = 0.5;
        if (toolContext == null || toolContext.getContext() == null
                || toolContext.getContext().isEmpty()) {
            log.error("ToolContext is null or empty, cannot scroll");
            return "工具执行失败";
        }
        Map<String, Object> context = toolContext.getContext();
        WebSocketSession session = (WebSocketSession)context.get("session");
        Action action = new Action("scroll", Map.of("clicks", clicks));
        String result = MyWebSocketHandler.sendRequestAndWait(session, "正在执行工具 scroll", Collections.singletonList(action));
        return StrUtil.isBlank(result) ? "工具执行失败" : String.format("Scroll %d units with wait %.2f", clicks, wait);
    }

    @Tool(description = "Drag the mouse from a start position to an end position.")
    public String dragMouse(
            @ToolParam(description = "Start X coordinate") int startX,
            @ToolParam(description = "Start Y coordinate") int startY,
            @ToolParam(description = "End X coordinate") int endX,
            @ToolParam(description = "End Y coordinate") int endY,
            ToolContext toolContext
    ) {
        double duration = 1.0; // fixed default duration
        if (toolContext == null || toolContext.getContext() == null
                || toolContext.getContext().isEmpty()) {
            log.error("ToolContext is null or empty, cannot drag mouse");
            return "工具执行失败";
        }
        Map<String, Object> context = toolContext.getContext();
        WebSocketSession session = (WebSocketSession)context.get("session");
        Action action = new Action("drag_mouse", Map.of("start_x",startX,"start_y",startY,"end_x",endX,"end_y",endY));
        String result = MyWebSocketHandler.sendRequestAndWait(session, "正在执行工具 drag_mouse", Collections.singletonList(action));
        return StrUtil.isBlank(result) ? "工具执行失败" : String.format("Drag from (%d,%d) to (%d,%d) duration %.2f", startX, startY, endX, endY, duration);
    }

    @Tool(description = "Press a single key (e.g., 'enter', 'esc', 'space', 'backspace').")
    public String pressKey(
            @ToolParam(description = "Key to press") String key,
            ToolContext toolContext
    ) {
        double wait = 0.5;
        if (toolContext == null || toolContext.getContext() == null
                || toolContext.getContext().isEmpty()) {
            log.error("ToolContext is null or empty, cannot press key");
            return "工具执行失败";
        }
        Map<String, Object> context = toolContext.getContext();
        WebSocketSession session = (WebSocketSession)context.get("session");
        Action action = new Action("press_key", Map.of("key", key));
        String result = MyWebSocketHandler.sendRequestAndWait(session, "正在执行工具 press_key", Collections.singletonList(action));
        return StrUtil.isBlank(result) ? "工具执行失败" : String.format("Press key '%s' with wait %.2f", key, wait);
    }

    @Tool(description = "Press a combination of keys (e.g., 'ctrl+c', 'alt+tab').")
    public String hotkey(
            @ToolParam(description = "Combination keys separated by '+'") String keys,
            ToolContext toolContext
    ) {
        double wait = 0.5;
        if (toolContext == null || toolContext.getContext() == null
                || toolContext.getContext().isEmpty()) {
            log.error("ToolContext is null or empty, cannot hotkey");
            return "工具执行失败";
        }
        Map<String, Object> context = toolContext.getContext();
        WebSocketSession session = (WebSocketSession)context.get("session");
        Action action = new Action("hotkey", Map.of("keys", keys));
        String result = MyWebSocketHandler.sendRequestAndWait(session, "正在执行工具 hotkey", Collections.singletonList(action));
        return StrUtil.isBlank(result) ? "工具执行失败" : String.format("Press hotkey '%s' with wait %.2f", keys, wait);
    }


    @Override
    public String getDescription() {
        return "Mouse and keyboard GUI action decision tools";
    }

    @Override
    public ToolCallback[] createTools() {
        return ToolCallbacks.from(new GUIToolFactory());
    }

    @Bean
    public ToolCallback[] guiTools() {
        return createTools();
    }


//    public ToolCallback[] getToolCallbacks() {
//        ToolCallback[] toolCallbacks =
//                (ToolCallback[]) this.toolObjects.stream().map(
//                        (toolObject) -> (ToolCallback[]) Stream.of(ReflectionUtils.getDeclaredMethods(toolObject.getClass()))
//                                .filter((toolMethod) -> toolMethod.isAnnotationPresent(Tool.class))
//                                .filter((toolMethod) -> !this.isFunctionalType(toolMethod))
//                                .map((toolMethod) -> MethodToolCallback.builder()
//                                                                .toolDefinition(ToolDefinition.from(toolMethod))
//                                                                .toolMetadata(ToolMetadata.from(toolMethod))
//                                                                .toolMethod(toolMethod).toolObject(toolObject)
//                                                                .toolCallResultConverter(ToolUtils.getToolCallResultConverter(toolMethod))
//                                                                .build())
//                                                                .toArray((x$0) -> new ToolCallback[x$0]))
//                                                                .flatMap(Stream::of)
//                                                                .toArray((x$0) -> new ToolCallback[x$0]);
//        this.validateToolCallbacks(toolCallbacks);
//        return toolCallbacks;
//    }
}