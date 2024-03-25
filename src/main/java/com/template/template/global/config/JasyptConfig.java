package com.template.template.global.config;

import com.template.template.global.common.Log;
import com.template.template.global.util.CustomUtil;
import com.ulisesbocchio.jasyptspringboot.annotation.EnableEncryptableProperties;
import org.jasypt.encryption.StringEncryptor;
import org.jasypt.encryption.pbe.PooledPBEStringEncryptor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.Resource;

import java.io.FileNotFoundException;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.stream.Collectors;

@Configuration
@EnableEncryptableProperties
public class JasyptConfig {

  private static final Logger log = LoggerFactory.getLogger(Log.class);

  @Value("${jasypt.encryptor.algorithm}")
  private String algorithm;
  @Value("${jasypt.encryptor.pool-size}")
  private int poolSize;
  @Value("${jasypt.encryptor.string-output-type}")
  private String stringOutputType;
  @Value("${jasypt.encryptor.key-obtention-iterations}")
  private int keyObtentionIterations;

  @Bean
  public StringEncryptor jasyptStringEncryptor() {
    String pw = readFile("pw.jasyptpw");
    log.info("pw : {}",pw);
    PooledPBEStringEncryptor encryptor = new PooledPBEStringEncryptor();
    encryptor.setPoolSize(poolSize);
    encryptor.setAlgorithm(algorithm);
    encryptor.setPassword(pw);
    encryptor.setStringOutputType(stringOutputType);
    encryptor.setKeyObtentionIterations(keyObtentionIterations);

    String plainText = "";
    String encryptedText = encryptor.encrypt(plainText);
    String decryptedText = encryptor.decrypt(encryptedText);

    log.info("encryptedText : {}",encryptedText);
    log.info("decryptedText : {}",decryptedText);

    return encryptor;

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