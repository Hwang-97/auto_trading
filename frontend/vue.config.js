const path = require('path');
module.exports = {
    pwa: {
        name: "autoTrading",
        start_url: "/login",
    },
    configureWebpack: {
        resolve: {
            // 경로에서 확장자 생략 설정
            extensions: ['.js', '.vue'],
            alias: {
                '@': path.join(__dirname, 'src/'),
                '@components': path.join(__dirname, 'src/components'),
                '@assets': path.join(__dirname, 'src/assets'),
            }
        }
    },
    chainWebpack: (config) => {
        config.module
            .rule("vue")
            .use("vue-loader")
            .tap((options) => {
                options.compiler = require("vue-template-babel-compiler");
                options.hotReload = false; // disables Hot Reload
                return options;
            });
    },
    css: {
        loaderOptions: {
            scss: {
                additionalData: `
          @import "${"@/style/reset.scss"}";
          @import "${"@/style/variable.scss"}";
        `,
            },
        }
    },
    // 개발 서버 옵션
    devServer: {
        host: 'localhost',
        port: 8080,
        hot: true,
        proxy: {
            '/api': {
                target: 'http://localhost:5657',
                changeOrigin: true,
                pathRewrite: {
                    '^/': ''
                }
            }
        }
    }
};
