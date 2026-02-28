/**
 * API Routes for E-commerce Application
 * Handles product management, cart operations, and order processing
 */

import express, { Request, Response, NextFunction } from 'express';

// Types
interface Product {
  id: number;
  name: string;
  description: string;
  price: number;
  stock: number;
  category: string;
  imageUrl?: string;
}

interface CartItem {
  productId: number;
  quantity: number;
  price: number;
}

interface Cart {
  userId: number;
  items: CartItem[];
  total: number;
  updatedAt: Date;
}

interface Order {
  orderId: number;
  userId: number;
  items: CartItem[];
  totalAmount: number;
  status: 'pending' | 'processing' | 'shipped' | 'delivered' | 'cancelled';
  createdAt: Date;
  shippingAddress: string;
}

// In-memory storage (replace with database in production)
const products: Map<number, Product> = new Map();
const carts: Map<number, Cart> = new Map();
const orders: Map<number, Order> = new Map();

const router = express.Router();

/**
 * Middleware to validate product ID
 */
function validateProductId(req: Request, res: Response, next: NextFunction): void {
  const productId = parseInt(req.params.id);

  if (isNaN(productId) || productId <= 0) {
    res.status(400).json({ error: 'Invalid product ID' });
    return;
  }

  next();
}

/**
 * Middleware to check authentication (simplified for demo)
 */
function requireAuth(req: Request, res: Response, next: NextFunction): void {
  const userId = req.headers['user-id'];

  if (!userId) {
    res.status(401).json({ error: 'Authentication required' });
    return;
  }

  (req as any).userId = parseInt(userId as string);
  next();
}

/**
 * GET /api/products
 * Retrieve all products with optional filtering
 */
router.get('/products', (req: Request, res: Response) => {
  const { category, minPrice, maxPrice, search } = req.query;

  let filteredProducts = Array.from(products.values());

  // Filter by category
  if (category) {
    filteredProducts = filteredProducts.filter(
      p => p.category.toLowerCase() === (category as string).toLowerCase()
    );
  }

  // Filter by price range
  if (minPrice) {
    filteredProducts = filteredProducts.filter(
      p => p.price >= parseFloat(minPrice as string)
    );
  }
  if (maxPrice) {
    filteredProducts = filteredProducts.filter(
      p => p.price <= parseFloat(maxPrice as string)
    );
  }

  // Search in name and description
  if (search) {
    const searchTerm = (search as string).toLowerCase();
    filteredProducts = filteredProducts.filter(p =>
      p.name.toLowerCase().includes(searchTerm) ||
      p.description.toLowerCase().includes(searchTerm)
    );
  }

  res.json({
    success: true,
    count: filteredProducts.length,
    products: filteredProducts
  });
});

/**
 * GET /api/products/:id
 * Get a single product by ID
 */
router.get('/products/:id', validateProductId, (req: Request, res: Response) => {
  const productId = parseInt(req.params.id);
  const product = products.get(productId);

  if (!product) {
    res.status(404).json({ error: 'Product not found' });
    return;
  }

  res.json({ success: true, product });
});

/**
 * POST /api/products
 * Create a new product (admin only)
 */
router.post('/products', (req: Request, res: Response) => {
  const { name, description, price, stock, category, imageUrl } = req.body;

  // Validation
  if (!name || !price || stock === undefined) {
    res.status(400).json({ error: 'Missing required fields' });
    return;
  }

  const productId = products.size + 1;
  const newProduct: Product = {
    id: productId,
    name,
    description: description || '',
    price: parseFloat(price),
    stock: parseInt(stock),
    category: category || 'general',
    imageUrl
  };

  products.set(productId, newProduct);

  res.status(201).json({
    success: true,
    message: 'Product created successfully',
    product: newProduct
  });
});

/**
 * POST /api/cart/add
 * Add item to shopping cart
 */
router.post('/cart/add', requireAuth, (req: Request, res: Response) => {
  const userId = (req as any).userId;
  const { productId, quantity } = req.body;

  // Validate product exists and has stock
  const product = products.get(productId);
  if (!product) {
    res.status(404).json({ error: 'Product not found' });
    return;
  }

  if (product.stock < quantity) {
    res.status(400).json({ error: 'Insufficient stock' });
    return;
  }

  // Get or create cart
  let cart = carts.get(userId);
  if (!cart) {
    cart = {
      userId,
      items: [],
      total: 0,
      updatedAt: new Date()
    };
    carts.set(userId, cart);
  }

  // Check if item already in cart
  const existingItem = cart.items.find(item => item.productId === productId);

  if (existingItem) {
    existingItem.quantity += quantity;
  } else {
    cart.items.push({
      productId,
      quantity,
      price: product.price
    });
  }

  // Update total
  cart.total = cart.items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
  cart.updatedAt = new Date();

  res.json({
    success: true,
    message: 'Item added to cart',
    cart
  });
});

/**
 * GET /api/cart
 * Get user's shopping cart
 */
router.get('/cart', requireAuth, (req: Request, res: Response) => {
  const userId = (req as any).userId;
  const cart = carts.get(userId);

  if (!cart) {
    res.json({
      success: true,
      cart: { userId, items: [], total: 0 }
    });
    return;
  }

  res.json({ success: true, cart });
});

/**
 * POST /api/orders/checkout
 * Process checkout and create order
 */
router.post('/orders/checkout', requireAuth, (req: Request, res: Response) => {
  const userId = (req as any).userId;
  const { shippingAddress } = req.body;

  if (!shippingAddress) {
    res.status(400).json({ error: 'Shipping address required' });
    return;
  }

  const cart = carts.get(userId);
  if (!cart || cart.items.length === 0) {
    res.status(400).json({ error: 'Cart is empty' });
    return;
  }

  // Verify stock availability
  for (const item of cart.items) {
    const product = products.get(item.productId);
    if (!product || product.stock < item.quantity) {
      res.status(400).json({
        error: `Insufficient stock for product ID ${item.productId}`
      });
      return;
    }
  }

  // Create order
  const orderId = orders.size + 1;
  const order: Order = {
    orderId,
    userId,
    items: [...cart.items],
    totalAmount: cart.total,
    status: 'pending',
    createdAt: new Date(),
    shippingAddress
  };

  orders.set(orderId, order);

  // Update product stock
  for (const item of cart.items) {
    const product = products.get(item.productId)!;
    product.stock -= item.quantity;
  }

  // Clear cart
  carts.delete(userId);

  res.status(201).json({
    success: true,
    message: 'Order placed successfully',
    order
  });
});

/**
 * GET /api/orders/:orderId
 * Get order details
 */
router.get('/orders/:orderId', requireAuth, (req: Request, res: Response) => {
  const userId = (req as any).userId;
  const orderId = parseInt(req.params.orderId);

  const order = orders.get(orderId);

  if (!order) {
    res.status(404).json({ error: 'Order not found' });
    return;
  }

  // Verify order belongs to user
  if (order.userId !== userId) {
    res.status(403).json({ error: 'Unauthorized access to order' });
    return;
  }

  res.json({ success: true, order });
});

export default router;
