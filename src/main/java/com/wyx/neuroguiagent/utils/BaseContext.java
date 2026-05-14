package com.wyx.neuroguiagent.utils;

import java.util.HashMap;
import java.util.Map;

public class BaseContext {
    // 维护一个存放 Map 的 ThreadLocal
    private static final ThreadLocal<Map<String, Object>> THREAD_LOCAL = ThreadLocal.withInitial(HashMap::new);

    public static void put(String key, Object value) {
        THREAD_LOCAL.get().put(key, value);
    }

    public static Object get(String key) {
        return THREAD_LOCAL.get().get(key);
    }

    public static void remove() {
        THREAD_LOCAL.remove();
    }
}