import { FastifyPluginAsync } from 'fastify';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import speakeasy from 'speakeasy';
import QRCode from 'qrcode';
import { z } from 'zod';

const LoginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(6),
  totpCode: z.string().optional(),
});

const RegisterSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  name: z.string().optional(),
});

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret-key';

const authRoutes: FastifyPluginAsync = async (fastify) => {
  // Register
  fastify.post('/register', async (request, reply) => {
    try {
      const { email, password, name } = RegisterSchema.parse(request.body);
      
      // Check if user exists
      const existingUser = await fastify.prisma.user.findUnique({
        where: { email },
      });
      
      if (existingUser) {
        return reply.status(400).send({ error: 'User already exists' });
      }
      
      // Hash password
      const passwordHash = await bcrypt.hash(password, 12);
      
      // Create user
      const user = await fastify.prisma.user.create({
        data: {
          email,
          passwordHash,
          name: name || null,
        },
      });
      
      // Generate JWT
      const token = jwt.sign(
        { userId: user.id, email: user.email },
        JWT_SECRET,
        { expiresIn: '7d' }
      );
      
      return reply.send({
        token,
        user: {
          id: user.id,
          email: user.email,
          name: user.name,
        },
      });
      
    } catch (error) {
      fastify.log.error('Registration error:', error);
      return reply.status(400).send({ error: 'Registration failed' });
    }
  });

  // Login
  fastify.post('/login', async (request, reply) => {
    try {
      const { email, password, totpCode } = LoginSchema.parse(request.body);
      
      // Find user
      const user = await fastify.prisma.user.findUnique({
        where: { email },
      });
      
      if (!user || !user.isActive) {
        return reply.status(401).send({ error: 'Invalid credentials' });
      }
      
      // Verify password
      const isValidPassword = await bcrypt.compare(password, user.passwordHash);
      if (!isValidPassword) {
        return reply.status(401).send({ error: 'Invalid credentials' });
      }
      
      // Verify TOTP if enabled
      if (user.totpEnabled && user.totpSecret) {
        if (!totpCode) {
          return reply.status(401).send({ error: 'TOTP code required' });
        }
        
        const isValidTotp = speakeasy.totp.verify({
          secret: user.totpSecret,
          encoding: 'base32',
          token: totpCode,
          window: 2,
        });
        
        if (!isValidTotp) {
          return reply.status(401).send({ error: 'Invalid TOTP code' });
        }
      }
      
      // Update last login
      await fastify.prisma.user.update({
        where: { id: user.id },
        data: { lastLoginAt: new Date() },
      });
      
      // Generate JWT
      const token = jwt.sign(
        { userId: user.id, email: user.email },
        JWT_SECRET,
        { expiresIn: '7d' }
      );
      
      return reply.send({
        token,
        user: {
          id: user.id,
          email: user.email,
          name: user.name,
          totpEnabled: user.totpEnabled,
        },
      });
      
    } catch (error) {
      fastify.log.error('Login error:', error);
      return reply.status(400).send({ error: 'Login failed' });
    }
  });

  // Setup TOTP
  fastify.post('/totp/setup', {
    preHandler: [fastify.authenticate],
  }, async (request, reply) => {
    try {
      const userId = (request as any).userId;
      
      // Generate secret
      const secret = speakeasy.generateSecret({
        issuer: 'TradingView Gateway',
        name: `TradingView Gateway (${(request as any).userEmail})`,
        length: 32,
      });
      
      // Generate QR code
      const qrCodeUrl = await QRCode.toDataURL(secret.otpauth_url!);
      
      // Save secret (but don't enable yet)
      await fastify.prisma.user.update({
        where: { id: userId },
        data: { totpSecret: secret.base32 },
      });
      
      return reply.send({
        secret: secret.base32,
        qrCode: qrCodeUrl,
      });
      
    } catch (error) {
      fastify.log.error('TOTP setup error:', error);
      return reply.status(500).send({ error: 'TOTP setup failed' });
    }
  });

  // Enable TOTP
  fastify.post('/totp/enable', {
    preHandler: [fastify.authenticate],
  }, async (request, reply) => {
    try {
      const userId = (request as any).userId;
      const { totpCode } = z.object({ totpCode: z.string() }).parse(request.body);
      
      const user = await fastify.prisma.user.findUnique({
        where: { id: userId },
      });
      
      if (!user?.totpSecret) {
        return reply.status(400).send({ error: 'TOTP not set up' });
      }
      
      // Verify code
      const isValid = speakeasy.totp.verify({
        secret: user.totpSecret,
        encoding: 'base32',
        token: totpCode,
        window: 2,
      });
      
      if (!isValid) {
        return reply.status(400).send({ error: 'Invalid TOTP code' });
      }
      
      // Enable TOTP
      await fastify.prisma.user.update({
        where: { id: userId },
        data: { totpEnabled: true },
      });
      
      return reply.send({ message: 'TOTP enabled successfully' });
      
    } catch (error) {
      fastify.log.error('TOTP enable error:', error);
      return reply.status(500).send({ error: 'TOTP enable failed' });
    }
  });
};

// Authentication middleware
declare module 'fastify' {
  interface FastifyInstance {
    authenticate: any;
  }
}

export { authRoutes };