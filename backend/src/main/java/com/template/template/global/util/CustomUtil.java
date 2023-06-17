package com.template.template.global.util;

import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.Resource;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.io.FileNotFoundException;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.stream.Collectors;

public class CustomUtil {
    public String hashPassword(String password) {
        PasswordEncoder passwordEncoder = new BCryptPasswordEncoder();
        return passwordEncoder.encode(password);
    }

    public String readFile(String fileName) {
        try {
            Resource resource = new ClassPathResource(fileName);
            if (!resource.exists()) {
                throw new FileNotFoundException("File not found: " + fileName);
            }
            String result = Files.readAllLines(Paths.get(resource.getURI()))
                                .stream()
                                .collect(Collectors.joining(""));
            return result;
        } catch (IOException e) {
            throw new RuntimeException("Error reading file: " + fileName, e);
        }
    }
}
