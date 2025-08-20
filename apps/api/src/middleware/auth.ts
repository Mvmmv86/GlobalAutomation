import { FastifyRequest, FastifyReply } from 'fastify';
import jwt from 'jsonwebtoken';

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret-key';

interface JWTPayload {
  userId: string;
  email: string;
}

export async function authenticate(request: FastifyRequest, reply: FastifyReply) {
  try {
    const authHeader = request.headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return reply.status(401).send({ error: 'No token provided' });
    }
    
    const token = authHeader.slice(7);
    const decoded = jwt.verify(token, JWT_SECRET) as JWTPayload;
    
    // Add user info to request
    (request as any).userId = decoded.userId;
    (request as any).userEmail = decoded.email;
    
  } catch (error) {
    return reply.status(401).send({ error: 'Invalid token' });
  }
}