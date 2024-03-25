package com.template.template.domain.user.exception;

public class UserException extends Exception{
    public UserException(){
        super("user exception");
    }

    public UserException(String message){
        super(message);
    }
}
