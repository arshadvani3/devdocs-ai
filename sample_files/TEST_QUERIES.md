# Sample Test Queries

After uploading the sample files, try these questions to test the RAG system:

## Questions about auth_service.py

1. **How does the authentication system work?**
   - Should retrieve the `authenticate_user` function and JWT token generation

2. **How are passwords stored and verified?**
   - Should explain the hashing with SHA-256 and salt mechanism

3. **What is the token expiry time?**
   - Should find `token_expiry_hours = 24`

4. **How do I register a new user?**
   - Should retrieve the `register_user` function with validation logic

5. **What exceptions can be raised during authentication?**
   - Should find `AuthenticationError` class and its usage

## Questions about api_routes.ts

1. **How do I add items to the shopping cart?**
   - Should retrieve the `POST /cart/add` endpoint

2. **What product filters are available?**
   - Should explain category, minPrice, maxPrice, and search filters

3. **How does the checkout process work?**
   - Should retrieve the `POST /orders/checkout` endpoint with stock verification

4. **What authentication middleware is used?**
   - Should find `requireAuth` function

5. **How are products searched?**
   - Should explain the search filtering logic in GET /products

## Questions about ARCHITECTURE.md

1. **c**
   - Should list PostgreSQL, MongoDB, Redis

2. **How does the caching strategy work?**
   - Should explain three-layer caching with TTLs

3. **What are the performance targets?**
   - Should list P95 latency, throughput, uptime targets

4. **How is security implemented?**
   - Should retrieve JWT, bcrypt, HTTPS, rate limiting details

5. **What microservices are available?**
   - Should list Auth, Product, Cart, Order, Notification services

## General Questions (Cross-file)

1. **How is user authentication handled across the system?**
   - Should retrieve info from both auth_service.py and ARCHITECTURE.md

2. **What technologies are used for caching?**
   - Should find Redis from both api_routes.ts and ARCHITECTURE.md

3. **How are orders processed?**
   - Should combine info from api_routes.ts checkout flow and ARCHITECTURE.md

## Testing Tips

- Try variations of the same question to test semantic search
- Ask follow-up questions about specific functions or components
- Test with technical terms (JWT, Redis, PostgreSQL) vs natural language
- Check if source citations point to correct files and line numbers
- Verify that code snippets in responses are accurate
