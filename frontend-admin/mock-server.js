#!/usr/bin/env node

const express = require('express')
const cors = require('cors')

const app = express()
const PORT = 8001

// Middleware
app.use(cors())
app.use(express.json())

// Mock data
const mockPositions = [
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
  },
  {
    id: '2',
    symbol: 'ETHUSDT',
    side: 'short',
    size: 2.5,
    entryPrice: 2650.80,
    currentPrice: 2634.20,
    pnl: 41.50,
    pnlPercent: 0.63,
    leverage: 5,
    margin: 1325.40
  }
]

const mockOrders = [
  {
    id: '1',
    symbol: 'ADAUSDT',
    side: 'buy',
    type: 'limit',
    amount: 1000,
    price: 0.45,
    status: 'pending'
  }
]

const mockAccounts = [
  {
    id: 'binance-main',
    name: 'Binance Principal',
    exchange: 'binance',
    balance: 15420.85,
    availableBalance: 12250.30,
    currency: 'USDT'
  },
  {
    id: 'bybit-demo',
    name: 'Bybit Demo',
    exchange: 'bybit', 
    balance: 8750.20,
    availableBalance: 7100.15,
    currency: 'USDT'
  }
]

const mockPrices = {
  'BTCUSDT': { price: 43580.50, change: 2.1, changePercent: 4.85 },
  'ETHUSDT': { price: 2634.20, change: -15.8, changePercent: -0.59 },
  'ADAUSDT': { price: 0.457, change: 0.012, changePercent: 2.69 }
}

// Routes
app.get('/api/v1/', (req, res) => {
  res.json({
    service: 'Mock Trading API',
    status: 'healthy'
  })
})

app.get('/api/v1/positions', (req, res) => {
  res.json({
    success: true,
    data: mockPositions
  })
})

app.get('/api/v1/orders', (req, res) => {
  res.json({
    success: true,
    data: mockOrders
  })
})

app.get('/api/v1/accounts', (req, res) => {
  res.json({
    success: true,
    data: mockAccounts
  })
})

app.get('/api/v1/prices', (req, res) => {
  res.json({
    success: true,
    data: mockPrices
  })
})

app.get('/api/v1/prices/:symbol', (req, res) => {
  const { symbol } = req.params
  const price = mockPrices[symbol.toUpperCase()]
  
  if (!price) {
    return res.status(404).json({
      success: false,
      error: 'Symbol not found'
    })
  }
  
  res.json({
    success: true,
    data: price
  })
})

app.post('/api/v1/orders', (req, res) => {
  const order = {
    id: Math.random().toString(36).substr(2, 9),
    ...req.body,
    status: 'pending',
    timestamp: new Date().toISOString()
  }
  
  mockOrders.push(order)
  
  res.status(201).json({
    success: true,
    data: order
  })
})

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok' })
})

app.listen(PORT, () => {
  console.log(`🚀 Mock API server running on http://localhost:${PORT}`)
  console.log(`📊 Available endpoints:`)
  console.log(`   GET  /api/v1/ - API info`)
  console.log(`   GET  /api/v1/positions - Trading positions`)
  console.log(`   GET  /api/v1/orders - Open orders`)
  console.log(`   GET  /api/v1/accounts - Trading accounts`)
  console.log(`   GET  /api/v1/prices - All prices`)
  console.log(`   GET  /api/v1/prices/:symbol - Single price`)
  console.log(`   POST /api/v1/orders - Create order`)
})