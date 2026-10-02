package com.omniai.connector;

import java.util.Map;
import java.util.UUID;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {
    @GetMapping("/api/v1/health")
    public ResponseEntity<Map<String, Object>> health(@RequestHeader(value = "X-Request-ID", required = false) String incomingId) {
        String requestId = incomingId == null || incomingId.isBlank() ? UUID.randomUUID().toString() : incomingId;
        return ResponseEntity.ok().header("X-Request-ID", requestId).body(Map.of(
            "ok", true,
            "service", "omniai-enterprise-spring",
            "version", "0.1.0",
            "request_id", requestId
        ));
    }
}
