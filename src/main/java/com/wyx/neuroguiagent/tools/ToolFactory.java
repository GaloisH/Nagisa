package com.wyx.neuroguiagent.tools;

import org.springframework.ai.tool.ToolCallback;

// 工厂模式：一个工厂只创建一种产品
public interface ToolFactory {

    String getDescription();

    ToolCallback[] createTools();
}
