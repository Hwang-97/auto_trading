package com.template.template.global.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod; // Import HttpMethod class
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configuration.WebSecurityConfigurerAdapter;
import org.springframework.security.web.util.matcher.RequestHeaderRequestMatcher;

@Configuration
@EnableWebSecurity
public class SecurityConfig extends WebSecurityConfigurerAdapter {

    @Override
    protected void configure(HttpSecurity http) throws Exception {

        http.authorizeRequests()
            .antMatchers(HttpMethod.GET, "/public/**").permitAll()
            .anyRequest().authenticated()
            .and().requestMatcher(new RequestHeaderRequestMatcher("X-Forwarded-For"));
    }
}
