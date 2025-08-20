import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcryptjs';
import { encryptCredentials } from '@tradingview-gateway/shared';

const prisma = new PrismaClient();

async function main() {
  console.log('🌱 Starting database seeding...');

  // Create admin user
  const adminEmail = 'admin@tradingview-gateway.com';
  const adminPassword = 'admin123456';
  
  const existingAdmin = await prisma.user.findUnique({
    where: { email: adminEmail },
  });

  let adminUser;
  
  if (existingAdmin) {
    console.log('👤 Admin user already exists');
    adminUser = existingAdmin;
  } else {
    const passwordHash = await bcrypt.hash(adminPassword, 12);
    
    adminUser = await prisma.user.create({
      data: {
        email: adminEmail,
        passwordHash,
        name: 'Administrator',
        isActive: true,
      },
    });
    
    console.log('👤 Admin user created:', adminEmail);
    console.log('🔑 Admin password:', adminPassword);
  }

  // Create demo exchange accounts (using fake credentials for testnet)
  const demoAccounts = [
    {
      name: 'Binance Testnet Demo',
      exchange: 'binance',
      apiKey: 'demo_binance_api_key',
      secretKey: 'demo_binance_secret_key',
      testnet: true,
    },
    {
      name: 'Bybit Testnet Demo',
      exchange: 'bybit',
      apiKey: 'demo_bybit_api_key',
      secretKey: 'demo_bybit_secret_key',
      testnet: true,
    },
  ];

  for (const accountData of demoAccounts) {
    const existingAccount = await prisma.exchangeAccount.findFirst({
      where: {
        userId: adminUser.id,
        name: accountData.name,
      },
    });

    if (existingAccount) {
      console.log(`🏦 Account already exists: ${accountData.name}`);
      continue;
    }

    const encryptedCreds = encryptCredentials(
      accountData.apiKey,
      accountData.secretKey
    );

    await prisma.exchangeAccount.create({
      data: {
        userId: adminUser.id,
        name: accountData.name,
        exchange: accountData.exchange,
        encryptedApiKey: encryptedCreds.apiKey,
        encryptedSecretKey: encryptedCreds.secretKey,
        testnet: accountData.testnet,
        isActive: true,
      },
    });

    console.log(`🏦 Created account: ${accountData.name}`);
  }

  // Create some sample jobs for demonstration
  const sampleJobs = [
    {
      alertId: 'sample_btc_buy_001',
      accountId: (await prisma.exchangeAccount.findFirst({ 
        where: { exchange: 'binance' }
      }))?.id,
      webhook: {
        strategy: 'Demo Strategy',
        ticker: 'BTCUSDT',
        action: 'buy',
        size_mode: 'quote',
        size_value: 100,
        exchange: 'binance',
        market_type: 'futures',
        alert_id: 'sample_btc_buy_001',
      },
      status: 'completed',
      completedAt: new Date(Date.now() - 3600000), // 1 hour ago
    },
    {
      alertId: 'sample_eth_sell_001',
      accountId: (await prisma.exchangeAccount.findFirst({ 
        where: { exchange: 'bybit' }
      }))?.id,
      webhook: {
        strategy: 'Demo Strategy',
        ticker: 'ETHUSDT',
        action: 'sell',
        size_mode: 'quote',
        size_value: 50,
        exchange: 'bybit',
        market_type: 'perp',
        alert_id: 'sample_eth_sell_001',
      },
      status: 'completed',
      completedAt: new Date(Date.now() - 1800000), // 30 minutes ago
    },
    {
      alertId: 'sample_ada_buy_001',
      accountId: (await prisma.exchangeAccount.findFirst({ 
        where: { exchange: 'binance' }
      }))?.id,
      webhook: {
        strategy: 'Demo Strategy',
        ticker: 'ADAUSDT',
        action: 'buy',
        size_mode: 'quote',
        size_value: 25,
        exchange: 'binance',
        market_type: 'futures',
        alert_id: 'sample_ada_buy_001',
      },
      status: 'failed',
      lastError: 'Insufficient balance',
      retryCount: 3,
    },
  ];

  for (const jobData of sampleJobs) {
    if (!jobData.accountId) continue;
    
    const existingJob = await prisma.job.findUnique({
      where: { alertId: jobData.alertId },
    });

    if (existingJob) {
      console.log(`📋 Job already exists: ${jobData.alertId}`);
      continue;
    }

    await prisma.job.create({
      data: {
        alertId: jobData.alertId,
        accountId: jobData.accountId,
        userId: adminUser.id,
        webhook: jobData.webhook,
        status: jobData.status,
        lastError: jobData.lastError,
        retryCount: jobData.retryCount || 0,
        completedAt: jobData.completedAt,
      },
    });

    console.log(`📋 Created job: ${jobData.alertId}`);
  }

  console.log('✅ Database seeding completed!');
  console.log('\n📋 Summary:');
  console.log(`👤 Admin User: ${adminEmail}`);
  console.log(`🔑 Password: ${adminPassword}`);
  console.log(`🏦 Exchange Accounts: ${demoAccounts.length} created`);
  console.log(`📋 Sample Jobs: ${sampleJobs.length} created`);
  console.log('\n🚀 You can now start the application!');
}

main()
  .catch((e) => {
    console.error('❌ Seeding failed:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });