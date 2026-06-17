package com.wyx.neuroguiagent.common;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Action {
    private String command;      // 指令名称，如 SCREENSHOT, CALL_FUNC
    private Map<String, Object> params; // 额外参数，如截图的质量、函数参数等
}