package com.wyx.neuroguiagent.utils;

import lombok.extern.slf4j.Slf4j;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Base64;
import java.util.concurrent.ThreadLocalRandom;

@Slf4j
public class ImageSaveUtil {

    /**
     * 将 Base64 编码的 JPEG 保存到 resources/pictures 目录下
     * @param base64Data 纯 Base64 字符串
     * @return 保存后的绝对路径
     */
    /**
     * 将 Base64 编码的 JPEG 保存到 resources/pictures 目录下
     * @param base64Data 纯 Base64 字符串
     * @return 保存后的绝对路径，如果保存失败则返回 null
     */
    public static String saveBase64ImageAsJpeg(String base64Data) {
        // 判空保护
        if (base64Data == null || base64Data.isEmpty()) {
            log.error("保存图片失败: Base64 数据为空");
            return null;
        }

        try {

            long start = System.currentTimeMillis();

            // 1. 解码 Base64
            byte[] imageBytes = Base64.getDecoder().decode(base64Data);

            // 2. 生成文件名 (yyyy-MM-dd_HH-mm-ss)
            String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd_HH-mm-ss"));
            int randomNumber = ThreadLocalRandom.current().nextInt(1000, 10000);
            String fileName = String.format("%s_%d.jpeg", timestamp, randomNumber);

            // 3. 确定存储路径 (src/main/resources/pictures)
            Path projectResourcesPath = Paths.get(System.getProperty("user.dir"), "src", "main", "resources", "pictures");

            // 4. 确保文件夹存在
            if (!Files.exists(projectResourcesPath)) {
                Files.createDirectories(projectResourcesPath);
            }

            // 5. 写入文件
            Path targetFile = projectResourcesPath.resolve(fileName);
            Files.write(targetFile, imageBytes);

            log.info("{} 图片保存耗时 : {} ms", fileName, System.currentTimeMillis() - start);

            return targetFile.toAbsolutePath().toString();

        } catch (IllegalArgumentException e) {
            log.error("保存图片失败: Base64 格式无效", e);
        } catch (IOException e) {
            log.error("保存图片失败: 磁盘写入异常, path: resources/pictures", e);
        } catch (Exception e) {
            log.error("保存图片失败: 发生未知错误", e);
        }

        // 只要进入了上面的任何一个 catch，都会执行到这里
        return null;
    }
}