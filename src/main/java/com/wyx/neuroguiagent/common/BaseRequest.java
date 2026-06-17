package com.wyx.neuroguiagent.common;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
// 客户端的通用请求对象
// type为chat表明单纯用户提问，data 为提问内容,code为空（后续可能data里面也有用户提问时附带的图片，但和服务端要求客户端的截图是两个东西）
// type为screen shot 表示是对服务端截图请求的回应，data 为 base64编码图片
// type为action result 表示是对服务端执行工具请求的回应,data 为success或其他描述
public class BaseRequest {
    private String type;
    private String data;
    private Integer code;
    private String callId;
}
