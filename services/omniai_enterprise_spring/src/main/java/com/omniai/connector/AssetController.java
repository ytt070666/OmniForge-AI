package com.omniai.connector;

import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/assets")
public class AssetController {
    private static final Map<String, Map<String, String>> ASSETS = Map.of(
        "GW-01", Map.of("role", "edge-gateway", "site", "lab-a", "status", "active"),
        "DB-02", Map.of("role", "analytics-database", "site", "dc-1", "status", "maintenance")
    );

    @GetMapping("/{id}")
    public ResponseEntity<?> getAsset(@PathVariable String id, @RequestHeader(value = "X-Request-ID", required = false) String incomingId) {
        String requestId = incomingId == null || incomingId.isBlank() ? UUID.randomUUID().toString() : incomingId;
        var row = ASSETS.get(id.toUpperCase());
        if (row == null) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).header("X-Request-ID", requestId)
                .body(Map.of("error", Map.of("code", "ASSET_NOT_FOUND", "message", "asset not found", "request_id", requestId)));
        }
        return ResponseEntity.ok().header("X-Request-ID", requestId).body(Map.of("id", id.toUpperCase(), "record", row, "request_id", requestId));
    }
}
