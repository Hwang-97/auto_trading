package com.template.template.domain.user.repository;

import com.template.template.domain.user.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface UserRepository extends JpaRepository<User, Integer> {
    @Query( value = "SELECT * FROM board_detail WHERE ID = ?1", nativeQuery = true )
    Boolean login (@Param("userName")String userName, @Param("userPw")String userPw);

    boolean existsByUsername(String username);
}

