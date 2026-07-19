const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const gateway = express();

// 1. Forward all /v1 and /v2 traffic to your Python FastAPI server
gateway.use('/v1', createProxyMiddleware({ target: 'http://127.0.0.1:8000', changeOrigin: true }));
gateway.use('/v2', createProxyMiddleware({ target: 'http://127.0.0.1:8000', changeOrigin: true }));

// 2. Forward all /dog traffic to your Node.js random.dog server
gateway.use('/dog', createProxyMiddleware({ target: 'http://127.0.0.1:8080', changeOrigin: true }));

// 3. Start the gateway on port 5000
gateway.listen(5000, () => {
    console.log("Unified Gateway running on port 5000!");
});
