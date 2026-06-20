import React, { useState } from "react";
import axios from "axios";
import "../App.css";

function Login() {

    const [email, setEmail] =
        useState("");

    const [password, setPassword] =
        useState("");

    const loginUser = async () => {

        try {

            const response =
                await axios.post(
                    "http://127.0.0.1:8000/login",
                    {
                        email: email,
                        password: password,
                    }
                );

            localStorage.setItem(
                "token",
                response.data.access_token
            );

            alert("Login Successful!");

        } catch (error) {

            console.log(error);

            alert("Login Failed");

        }
    };

    return (
        <div className="container">

            <div className="card">

                <h1>Welcome Back 👋</h1>

                <p className="subtitle">
                    Login to continue
                </p>

                <input
                    type="email"
                    placeholder="Enter Email"
                    value={email}
                    onChange={(e) =>
                        setEmail(e.target.value)
                    }
                />

                <input
                    type="password"
                    placeholder="Enter Password"
                    value={password}
                    onChange={(e) =>
                        setPassword(e.target.value)
                    }
                />

                <button onClick={loginUser}>
                    Login
                </button>

                <p className="link">
                    Don’t have an account?{" "}

                    <span
                        onClick={() =>
                            window.location.href = "/"
                        }
                    >
                        Register
                    </span>
                </p>

            </div>

        </div>
    );
}

export default Login;