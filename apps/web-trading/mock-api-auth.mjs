#!/usr/bin/env node

import express from 'express'
import cors from 'cors'

const app = express()
const PORT = 8001

// Middleware
app.use(cors())
app.use(express.json())

// Mock database
const users = []
const sessions = new Map()

// Helper functions
function hashPassword(password) {
  // Simple mock hash (não use em produção!)
  return 'hash_' + Buffer.from(password).toString('base64')
}

function generateToken() {
  return 'token_' + Math.random().toString(36).substr(2, 15)
}

// Routes
app.get('/api/v1/', (req, res) => {
  res.json({
    service: 'Mock Trading API with Auth (ESM)',
    version: '1.0.0',
    environment: 'development',
    status: 'healthy'
  })
})

app.get('/api/v1/health/', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    version: '1.0.0',
    environment: 'development',
    services: {
      api: 'healthy',
      database: 'healthy',
      redis: 'healthy'
    }
  })
})

// Auth endpoints
app.post('/api/v1/auth/register', (req, res) => {
  const { email, password, name } = req.body
  
  // Check if user already exists
  if (users.find(u => u.email === email)) {
    return res.status(400).json({
      error: 'Bad Request',
      detail: 'User with this email already exists'
    })
  }
  
  // Create user
  const user = {
    id: `user_${Math.random().toString(36).substr(2, 9)}`,
    email,
    name,
    password_hash: hashPassword(password),
    is_active: true,
    is_verified: false,
    created_at: new Date().toISOString()
  }
  
  users.push(user)
  
  res.status(201).json({
    user_id: user.id,
    email: user.email,
    message: 'User registered successfully'
  })
})

app.post('/api/v1/auth/login', (req, res) => {
  const { email, password } = req.body
  
  // Find user
  const user = users.find(u => u.email === email)
  if (!user) {
    return res.status(401).json({
      error: 'Unauthorized',
      detail: 'Incorrect email or password'
    })
  }
  
  // Check password
  if (user.password_hash !== hashPassword(password)) {
    return res.status(401).json({
      error: 'Unauthorized', 
      detail: 'Incorrect email or password'
    })
  }
  
  // Generate tokens
  const accessToken = generateToken()
  const refreshToken = generateToken()
  
  // Store session
  sessions.set(accessToken, {
    userId: user.id,
    email: user.email,
    createdAt: new Date()
  })
  
  res.json({
    access_token: accessToken,
    refresh_token: refreshToken,
    expires_in: 1800 // 30 minutes
  })
})

app.get('/api/v1/auth/me', (req, res) => {
  const authHeader = req.headers.authorization
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({
      error: 'Unauthorized',
      detail: 'Missing or invalid authorization header'
    })
  }
  
  const token = authHeader.slice(7)
  const session = sessions.get(token)
  
  if (!session) {
    return res.status(401).json({
      error: 'Unauthorized',
      detail: 'Invalid or expired token'
    })
  }
  
  const user = users.find(u => u.id === session.userId)
  if (!user) {
    return res.status(404).json({
      error: 'Not Found',
      detail: 'User not found'
    })
  }
  
  res.json({
    id: user.id,
    email: user.email,
    name: user.name,
    is_active: user.is_active,
    is_verified: user.is_verified,
    created_at: user.created_at
  })
})

// Trading data endpoints (from previous mock)
app.get('/api/v1/positions', (req, res) => {
  res.json({
    success: true,
    data: [
      {
        id: '1',
        symbol: 'BTCUSDT',
        side: 'long',
        size: 0.5,
        entryPrice: 43250.00,
        currentPrice: 43580.50,
        pnl: 165.25,
        pnlPercent: 0.76,
        leverage: 10,
        margin: 2162.50
      }
    ]
  })
})

app.get('/api/v1/accounts', (req, res) => {
  res.json({
    success: true,
    data: [
      {
        id: 'binance-main',
        name: 'Binance Principal',
        exchange: 'binance',
        balance: 15420.85,
        availableBalance: 12250.30,
        currency: 'USDT'
      }
    ]
  })
})

app.listen(PORT, () => {
  console.log(`🚀 Mock API with Auth (ESM) running on http://localhost:${PORT}`)
  console.log(`📊 Test endpoints:`)
  console.log(`   POST /api/v1/auth/register - Register user`)
  console.log(`   POST /api/v1/auth/login - Login user`)
  console.log(`   GET  /api/v1/auth/me - Get current user`)
  console.log(`   GET  /api/v1/health/ - Health check`)
  console.log(`\n💡 Frontend: Update VITE_API_URL=http://localhost:8001`)
})