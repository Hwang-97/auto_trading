package com.template.template.domain.user.service.impl;

import com.template.template.domain.user.dto.UserDTO;
import com.template.template.domain.user.entity.User;
import com.template.template.domain.user.repository.UserRepository;
import com.template.template.domain.user.service.UserService;
import com.template.template.global.util.CustomUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.HashMap;

@Service
public class UserServiceImpl implements UserService {

    @Autowired
    UserRepository userRepository;

    private CustomUtil util;

    public Boolean login(UserDTO user){
        Boolean checkLogin = false;

        return checkLogin;
    }

    public boolean usernameExists(String username) {
        return userRepository.existsByUsername(username);
    }

    @Override
    public Boolean sign(HashMap<String, Object> data) {
        Boolean checkLogin = false;
        String pw = util.readFile("pw.jasyptpw");
        if(!pw.equals((String) data.get("pw")) || usernameExists((String) data.get("userId"))){
           return checkLogin;
        }else{
            User user = new User();
            user.setUsername((String) data.get("userId"));
            user.setPassword(util.hashPassword((String) data.get("userPw")));
            userRepository.save(user);
        }
        return checkLogin;
    }
}
