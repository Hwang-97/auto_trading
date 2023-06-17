package com.template.template.domain.user.controller;

import com.template.template.domain.user.dto.UserDTO;
import com.template.template.domain.user.exception.UserException;
import com.template.template.domain.user.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;

@RestController
@RequestMapping("/api/v1/user")
public class UserController extends UserException {
    @Autowired
    UserService userService;

    @PostMapping("/login")
    public ResponseEntity<Boolean> login(@RequestBody UserDTO user) throws UserException {
        Boolean checkLogin = false;
        if(user != null){
            checkLogin = userService.login(user);
        }else{
            throw new UserException();
        }
        return ResponseEntity.ok(checkLogin);
    }

    @PostMapping("/signup")
    public ResponseEntity<Boolean> signUp(@RequestBody UserDTO user,
                                          @RequestBody String passwd) throws UserException {
        Boolean checkLogin = false;
        HashMap<String,Object> data = new HashMap<String,Object>();
        data.put("userId",user.getUsername());
        data.put("userPw",user.getPassword());
        data.put("pw",passwd);
        if(user != null){
            checkLogin = userService.sign(data);
        }else{
            throw new UserException();
        }
        return ResponseEntity.ok(checkLogin);
    }
}
