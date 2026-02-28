# System Architecture Documentation

## Overview

This document describes the architecture of our microservices-based e-commerce platform. The system is designed for high availability, scalability, and fault tolerance.

## System Components

### Frontend Layer

The frontend is built with React and TypeScript, providing a responsive single-page application (SPA):

- **React 18** - Core UI framework with hooks and suspense
- **Redux Toolkit** - State management for cart, user session, and product catalog
- **React Query** - Server state management with automatic caching and refetching
- **TailwindCSS** - Utility-first styling framework
- **Vite** - Fast build tool and development server

### API Gateway

The API Gateway serves as the single entry point for all client requests:

```
Client → API Gateway → Microservices
```

**Responsibilities:**
- Request routing to appropriate microservices
- Authentication and authorization (JWT validation)
- Rate limiting (100 requests/minute per user)
- Request/response transformation
- CORS handling
- SSL termination

**Technology:** Kong API Gateway with Nginx

### Microservices

#### 1. Authentication Service

Handles user registration, login, and token management.

**Endpoints:**
- `POST /auth/register` - User registration
- `POST /auth/login` - User authentication
- `POST /auth/refresh` - Token refresh
- `POST /auth/logout` - Invalidate session

**Database:** PostgreSQL for user data
**Cache:** Redis for session tokens (30-minute TTL)

#### 2. Product Service

Manages product catalog, inventory, and search functionality.

**Endpoints:**
- `GET /products` - List products with filtering
- `GET /products/:id` - Get product details
- `POST /products` - Create product (admin only)
- `PUT /products/:id` - Update product
- `DELETE /products/:id` - Soft delete product

**Database:** MongoDB for product catalog
**Search:** Elasticsearch for full-text search
**Cache:** Redis for frequently accessed products (1-hour TTL)

#### 3. Cart Service

Handles shopping cart operations for logged-in users.

**Endpoints:**
- `GET /cart` - Get user's cart
- `POST /cart/add` - Add item to cart
- `PUT /cart/update` - Update item quantity
- `DELETE /cart/remove/:productId` - Remove item from cart
- `DELETE /cart/clear` - Clear entire cart

**Database:** Redis (primary storage for cart data)
**TTL:** 7 days for inactive carts

#### 4. Order Service

Processes orders, manages order lifecycle, and integrates with payment gateway.

**Endpoints:**
- `POST /orders/checkout` - Create order from cart
- `GET /orders/:id` - Get order details
- `GET /orders/user/:userId` - Get user's order history
- `PUT /orders/:id/cancel` - Cancel order (if not shipped)

**Database:** PostgreSQL for order records
**Message Queue:** RabbitMQ for async order processing
**Payment Integration:** Stripe API

#### 5. Notification Service

Sends email and SMS notifications for order updates.

**Events Handled:**
- Order confirmation
- Payment success/failure
- Shipping updates
- Delivery confirmation

**Technology:**
- SendGrid for emails
- Twilio for SMS
- RabbitMQ consumer for event-driven notifications

## Data Flow

### User Registration Flow

```
1. User submits registration form
2. Frontend validates input and calls API Gateway
3. API Gateway routes to Auth Service
4. Auth Service:
   - Validates email uniqueness
   - Hashes password with bcrypt
   - Creates user record in PostgreSQL
   - Returns success response
5. Frontend displays confirmation
```

### Order Checkout Flow

```
1. User clicks "Checkout" button
2. Frontend calls POST /orders/checkout
3. API Gateway validates JWT token
4. Order Service:
   a. Validates cart items and pricing
   b. Checks product availability (calls Product Service)
   c. Creates order record (status: PENDING)
   d. Publishes message to payment queue
5. Payment Worker:
   a. Processes payment via Stripe
   b. Updates order status (SUCCESS or FAILED)
   c. Publishes notification event
6. Notification Service sends confirmation email
7. Frontend displays order confirmation
```

## Database Schema

### Users Table (PostgreSQL)

```sql
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);
```

### Products Collection (MongoDB)

```json
{
  "_id": "ObjectId",
  "name": "Product Name",
  "description": "Product description",
  "price": 99.99,
  "stock": 100,
  "category": "electronics",
  "images": ["url1", "url2"],
  "metadata": {
    "brand": "BrandName",
    "model": "Model123",
    "weight": 1.5
  },
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

### Orders Table (PostgreSQL)

```sql
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    shipping_address TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_items (
    item_id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(order_id),
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    product_name VARCHAR(255) NOT NULL
);
```

## Caching Strategy

### Three-Layer Caching

1. **Browser Cache** - Static assets cached for 1 year
2. **CDN Cache** - Product images and CSS/JS bundles
3. **Redis Cache** - Application data:
   - User sessions: 30 minutes
   - Product details: 1 hour
   - Shopping carts: 7 days
   - Product listings: 15 minutes

### Cache Invalidation

- **Time-based**: Automatic expiry via TTL
- **Event-based**: Invalidate on product updates
- **Manual**: Admin dashboard for force invalidation

## Security Measures

### Authentication
- JWT tokens with 1-hour expiry
- Refresh tokens with 7-day expiry
- bcrypt password hashing (12 rounds)
- Rate limiting on login attempts (5 attempts/15 minutes)

### API Security
- HTTPS only (TLS 1.3)
- CORS restricted to known origins
- Input validation and sanitization
- SQL injection prevention (parameterized queries)
- XSS protection (CSP headers)

### Infrastructure
- Network segmentation (DMZ for API Gateway)
- Private subnets for databases
- Security groups restricting port access
- Regular security audits and dependency updates

## Monitoring and Observability

### Metrics (Prometheus)
- Request rate, latency, error rate (RED metrics)
- Database connection pool utilization
- Cache hit/miss rates
- Queue depth and processing time

### Logging (ELK Stack)
- Structured JSON logging
- Centralized log aggregation
- Log retention: 30 days

### Distributed Tracing (Jaeger)
- Request tracing across microservices
- Performance bottleneck identification
- Dependency mapping

### Alerting (PagerDuty)
- Error rate > 5%
- P95 latency > 500ms
- Database connection failures
- Service health check failures

## Deployment

### Infrastructure as Code
- **Terraform** for AWS infrastructure provisioning
- **Kubernetes** for container orchestration
- **Helm** for application deployment
- **ArgoCD** for GitOps-based deployments

### CI/CD Pipeline

```
Git Push → GitHub Actions → Build → Test → Docker Build →
Push to ECR → Deploy to K8s → Health Check →
Gradual Rollout (Canary)
```

### High Availability
- Multi-AZ deployment across 3 availability zones
- Auto-scaling: 2-10 pods per service
- Load balancing with AWS ALB
- Database replication (master-slave)
- Redis Sentinel for cache failover

## Performance Targets

- **API Response Time**: P95 < 200ms
- **Page Load Time**: < 2 seconds
- **Availability**: 99.9% uptime (8.76 hours downtime/year)
- **Throughput**: 1000 requests/second peak load
- **Database Queries**: < 50ms average

## Future Enhancements

1. **Machine Learning Recommendations** - Personalized product suggestions
2. **Real-time Inventory Updates** - WebSocket notifications for stock changes
3. **Multi-region Deployment** - Global CDN with regional API clusters
4. **GraphQL API** - Flexible querying for mobile applications
5. **Service Mesh** - Istio for advanced traffic management
