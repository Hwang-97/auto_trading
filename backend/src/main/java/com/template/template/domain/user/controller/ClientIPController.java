package com.template.template.domain.user.controller;
import com.template.template.global.common.Log;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import javax.servlet.http.HttpServletRequest;

@RestController
public class ClientIPController {
    private static final Logger log = LoggerFactory.getLogger(Log.class);
    @GetMapping("/getClientIP")
    public String getClientIP(HttpServletRequest request) {
        // 클라이언트의 IP 주소를 가져와서 반환합니다.
        String clientIP = request.getRemoteAddr();
        return clientIP;
    }
}
