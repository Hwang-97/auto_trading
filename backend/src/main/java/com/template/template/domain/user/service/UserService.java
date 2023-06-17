package com.template.template.domain.user.service;

import com.template.template.domain.user.dto.UserDTO;

import java.util.HashMap;

public interface UserService {

    public Boolean login(UserDTO user);

    public Boolean sign(HashMap<String,Object> data);

    public boolean usernameExists(String username);
}
