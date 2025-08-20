#!/usr/bin/env node
import { Command } from 'commander';
import { encryptApiKey, decryptApiKey } from '@tradingview-gateway/shared';
import { PrismaClient } from '@prisma/client';
const program = new Command();
const prisma = new PrismaClient();
program
    .name('tradingview-gateway-cli')
    .description('TradingView Gateway CLI utilities')
    .version('1.0.0');
program
    .command('encrypt')
    .description('Encrypt an API key or secret')
    .argument('<value>', 'The value to encrypt')
    .action((value) => {
    try {
        const encrypted = encryptApiKey(value);
        console.log('Encrypted value:', encrypted);
    }
    catch (error) {
        console.error('Encryption failed:', error);
        process.exit(1);
    }
});
program
    .command('decrypt')
    .description('Decrypt an encrypted API key or secret')
    .argument('<encrypted>', 'The encrypted value to decrypt')
    .action((encrypted) => {
    try {
        const decrypted = decryptApiKey(encrypted);
        console.log('Decrypted value:', decrypted);
    }
    catch (error) {
        console.error('Decryption failed:', error);
        process.exit(1);
    }
});
program
    .command('test-exchange')
    .description('Test exchange connection')
    .option('-e, --exchange <exchange>', 'Exchange name (binance|bybit)', 'binance')
    .option('-a, --account <id>', 'Account ID to test')
    .action(async (options) => {
    try {
        if (options.account) {
            const account = await prisma.exchangeAccount.findUnique({
                where: { id: options.account },
            });
            if (!account) {
                console.error('Account not found');
                process.exit(1);
            }
            console.log('Testing account:', account.name);
            console.log('Exchange:', account.exchange);
            console.log('Testnet:', account.testnet);
            // Here you would create the adapter and test the connection
            console.log('✅ Connection test would be performed here');
        }
        else {
            console.log('Please specify an account ID with -a flag');
            process.exit(1);
        }
    }
    catch (error) {
        console.error('Test failed:', error);
        process.exit(1);
    }
    finally {
        await prisma.$disconnect();
    }
});
program
    .command('list-accounts')
    .description('List all exchange accounts')
    .option('-u, --user <email>', 'Filter by user email')
    .action(async (options) => {
    try {
        const where = {};
        if (options.user) {
            where.user = {
                email: options.user,
            };
        }
        const accounts = await prisma.exchangeAccount.findMany({
            where,
            include: {
                user: {
                    select: {
                        email: true,
                        name: true,
                    },
                },
            },
        });
        console.log('\n📋 Exchange Accounts:');
        console.log('─'.repeat(80));
        for (const account of accounts) {
            console.log(`ID: ${account.id}`);
            console.log(`Name: ${account.name}`);
            console.log(`Exchange: ${account.exchange.toUpperCase()}`);
            console.log(`Testnet: ${account.testnet ? 'Yes' : 'No'}`);
            console.log(`Active: ${account.isActive ? 'Yes' : 'No'}`);
            console.log(`User: ${account.user.name} (${account.user.email})`);
            console.log(`Created: ${account.createdAt.toISOString()}`);
            console.log('─'.repeat(40));
        }
        console.log(`\nTotal: ${accounts.length} accounts`);
    }
    catch (error) {
        console.error('Failed to list accounts:', error);
        process.exit(1);
    }
    finally {
        await prisma.$disconnect();
    }
});
program
    .command('generate-webhook')
    .description('Generate sample TradingView webhook payloads')
    .option('-e, --exchange <exchange>', 'Exchange (binance|bybit)', 'binance')
    .option('-s, --symbol <symbol>', 'Trading symbol', 'BTCUSDT')
    .option('-a, --action <action>', 'Action (buy|sell|close)', 'buy')
    .action((options) => {
    const samplePayloads = {
        binance: {
            strategy: 'Sample Strategy',
            ticker: options.symbol,
            action: options.action,
            size_mode: 'quote',
            size_value: 100,
            leverage: 10,
            stop_loss: options.action === 'buy' ? 45000 : 55000,
            take_profit: options.action === 'buy' ? 55000 : 45000,
            exchange: 'binance',
            market_type: 'futures',
            alert_id: `sample_${options.symbol.toLowerCase()}_${options.action}_${Date.now()}`,
        },
        bybit: {
            strategy: 'Sample Strategy',
            ticker: options.symbol,
            action: options.action,
            size_mode: 'contracts',
            size_value: 0.1,
            leverage: 5,
            exchange: 'bybit',
            market_type: 'perp',
            alert_id: `sample_${options.symbol.toLowerCase()}_${options.action}_${Date.now()}`,
        },
    };
    console.log('\n🔗 Sample TradingView Webhook Payload:');
    console.log('─'.repeat(50));
    console.log(JSON.stringify(samplePayloads[options.exchange], null, 2));
    console.log('\n📡 Webhook URL: http://your-domain.com/webhook/tv');
    console.log('🔐 Don\'t forget to set the webhook secret in TradingView!');
});
program.parse();
export default program;
