# Social Payment App on GenLayer

A complete **GenLayer Intelligent Contract** for a decentralized social payment application.

## Features

✅ **User Profiles** – Create a username (alphanumeric + underscore) and bio  
✅ **GEN Payments** – Send native GEN to users by username  
✅ **ERC-20 Tokens** – Send any ERC-20 token to users by username  
✅ **Money Requests** – Request payments from other users  
✅ **Social Feed** – Post messages (up to 1000 chars)  
✅ **Post Tips** – Tip posts with native GEN  
✅ **Transaction History** – Complete audit trail per user  
✅ **Follow System** – Follow and unfollow other users  

## What This Does

This contract enables a social-first payment experience on GenLayer:

1. **Profiles** – Users register with a validated username (3-32 chars, alphanumeric + underscore) and optional bio (max 500 chars)
2. **Payments** – Send funds directly to another user's username
3. **Requests** – Ask for money from friends/colleagues with a custom message
4. **Social Feed** – Post short messages (up to 1000 chars)
5. **Tipping** – Send tips to posts you like
6. **History** – View all transactions (paginated)
7. **Following** – Build a social graph

## Project Structure

```
genlayer-social-payment-app/
├── contract/
│   └── social_payment_app.py       (Main contract code, 800+ lines)
├── tests/
│   └── direct/
│       └── test_social_payment_app.py   (Direct test scaffold)
├── README.md                       (This file)
├── requirements.txt                (Python dependencies)
└── .gitignore
```

## Current Version

**SocialPaymentApp v1.1.0**

Key improvements:
- GenLayer dependency header included
- Proper validation for usernames (alphanumeric + underscore only)
- Bio length limit (500 chars)
- Safer storage pattern for persistent records
- Complete documentation with examples
- Test scaffold included

## GenLayer Dependency

This contract requires the GenLayer SDK. The dependency header is included:

```python
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
```

## Deploying in GenLayer Studio

### Step 1: Open GenLayer Studio

Go to [GenLayer Studio](https://genlayer.studio) (or your local environment)

### Step 2: Create a New Contract

- Click **"New Contract"**
- Select **"Python"**

### Step 3: Copy the Contract Code

- Open `contract/social_payment_app.py`
- Copy the entire Python code
- Paste into GenLayer Studio editor

### Step 4: Compile

- Click **"Compile"**
- Fix any errors if they appear

### Step 5: Deploy

- Click **"Deploy"**
- Approve the transaction
- Save the contract address

## Validating Locally

Before deploying to GenLayer Studio, validate the contract:

```bash
# Install dependencies
pip install -r requirements.txt

# Run direct tests
pytest tests/direct/ -v
```

## How to Interact with It

### 1. Create a Profile

```python
contract.create_profile(
    username="alice",
    bio="Building on GenLayer"
)
```

**Username rules:**
- Minimum 3 characters
- Maximum 32 characters  
- Alphanumeric (a-z, 0-9) and underscore only
- Stored as lowercase

**Bio rules:**
- Maximum 500 characters

### 2. Get Your Profile

```python
profile = contract.get_my_profile()
print(profile.username)  # "alice"
print(profile.bio)       # "Building on GenLayer"
```

### 3. Resolve a Username

```python
bob_address = contract.resolve_username("bob")
```

### 4. Send GEN to Another User

```python
contract.send_gen(
    username="bob",
    note="Thanks for the help!"
)
```

**Important:** Attach GEN as transaction value:
- **GenLayer Studio UI:** Use the transaction value field
- **API:** Include `value` in the transaction

### 5. Send ERC-20 Tokens

First, approve the contract:

```python
token_contract.approve(
    spender=social_pay_address,
    amount=1000
)
```

Then send:

```python
contract.send_token(
    username="carol",
    token_address="0xYourTokenContractAddress",
    amount=1000,
    note="Payment for design work"
)
```

### 6. Request Money

```python
request_id = contract.request_money(
    username="dave",
    amount=50,
    token_address="0x0000000000000000000000000000000000000000",  # GEN
    note="Lunch today?"
)
# Returns: 1, 2, 3, ... (request ID)
```

### 7. Pay a GEN Request

```python
contract.pay_request_gen(request_id=1)
```

**Must attach GEN value equal to the request amount.**

### 8. Pay a Token Request

First approve the token, then:

```python
contract.pay_request_token(request_id=2)
```

### 9. Create a Post

```python
post_id = contract.create_post(
    content="Just deployed my first GenLayer contract!"
)
# Returns: 1, 2, 3, ... (post ID)
```

**Post rules:**
- Cannot be empty
- Maximum 1000 characters

### 10. Tip a Post

```python
contract.tip_post(
    post_id=1,
    note="Great work!"
)
```

**Attach GEN value as the tip amount.**

### 11. View Transaction History

```python
# Get count
count = contract.get_user_transaction_count()

# Get first 20 transactions
transactions = contract.get_user_transactions(
    start_index=0,
    count=20
)

# Get next 20
transactions = contract.get_user_transactions(
    start_index=20,
    count=20
)
```

### 12. Follow a User

```python
contract.follow_user("bob")
```

### 13. View Followers/Following

```python
following = contract.get_following()
followers = contract.get_followers()
following_count = contract.get_following_count()
followers_count = contract.get_followers_count()
```

### 14. Unfollow a User

```python
contract.unfollow_user("bob")
```

### 15. Get App Info

```python
info = contract.get_app_info()
print(info)  # "SocialPaymentApp v1.1.0"
```

## Data Structures

### UserProfile

```python
@dataclass
class UserProfile:
    username: str       # Username (3-32 chars, lowercase)
    bio: str            # User bio (max 500 chars)
    created_at: str     # Timestamp of creation
```

### SocialPost

```python
@dataclass
class SocialPost:
    post_id: u256       # Unique post ID
    author: Address     # Post author's wallet
    content: str        # Post content (max 1000 chars)
    created_at: str     # Creation timestamp
    tips_received: u256 # Total GEN tips received
```

### MoneyRequest

```python
@dataclass
class MoneyRequest:
    request_id: u256    # Unique request ID
    requester: Address  # Who is requesting
    payer: Address      # Who should pay
    amount: u256        # Amount to pay
    token: Address      # Token address (zero = GEN)
    note: str           # Request message
    created_at: str     # Creation timestamp
    paid: bool          # Whether it was paid
```

### TransactionRecord

```python
@dataclass
class TransactionRecord:
    transaction_id: u256    # Unique transaction ID
    sender: Address         # Sender address
    recipient: Address      # Recipient address
    amount: u256            # Amount transferred
    token: Address          # Token address (zero = GEN)
    transaction_type: str   # GEN_PAYMENT, TOKEN_PAYMENT, REQUEST_PAYMENT, POST_TIP
    reference_id: u256      # Link to request/post (if applicable)
    note: str               # Transaction note
    timestamp: str          # When it happened
    status: str             # "submitted", "finalized", etc.
```

## Important Notes

### Zero Address

Zero address (`0x0000000000000000000000000000000000000000`) represents **native GEN**.

Any other address is treated as an **ERC-20 token contract**.

### Username Validation

Usernames are:
- **Case-insensitive** ("Alice" and "alice" are the same)
- **Normalized to lowercase** in storage
- **3-32 characters** long
- **Alphanumeric + underscore only** (no special chars, spaces, etc.)

### Token Approvals

Before sending ERC-20 tokens, the sender must approve the contract:

```python
token.approve(social_pay_contract_address, amount)
```

### Pagination

Transaction history is paginated. Use `start_index` and `count`:

```python
# Get 20 transactions starting from index 0
contract.get_user_transactions(start_index=0, count=20)

# Get next 20
contract.get_user_transactions(start_index=20, count=20)
```

### Storage Patterns

This contract uses GenLayer's persistent storage patterns:
- **TreeMap** for key-value storage
- **DynArray** for dynamic arrays
- **@allow_storage** for dataclass persistence
- Safer immutable record replacement pattern for updates

## Example End-to-End Flow

```python
# Alice creates a profile
alice.create_profile(username="alice", bio="Developer")

# Bob creates a profile
bob.create_profile(username="bob", bio="Designer")

# Alice sends 100 GEN to Bob
alice.send_gen(username="bob", note="Payment for design work")  # Attach 100 GEN

# Bob creates a post
post_id = bob.create_post(content="New design system complete!")

# Alice tips the post with 10 GEN
alice.tip_post(post_id=post_id, note="Amazing!")  # Attach 10 GEN

# Alice and Bob view their transaction history
alice_txns = alice.get_user_transactions(start_index=0, count=10)
bob_txns = bob.get_user_transactions(start_index=0, count=10)

# Alice follows Bob
alice.follow_user("bob")

# Check followers/following
print(alice.get_following_count())  # 1
print(bob.get_followers_count())    # 1
```

## Future Enhancements

Possible improvements:

- Likes and comments on posts
- User reputation system
- Trending posts and feeds
- Creator payouts
- Escrow for payments
- Dispute resolution
- Token price feeds
- Premium profiles

## Testing

Run the test scaffold:

```bash
pytest tests/direct/ -v
```

To add full integration tests, use GenLayer's Python testing framework with the contract's public methods.

## License

MIT

## Support

For questions or issues:

1. Check GenLayer documentation
2. Review contract code comments
3. Test in GenLayer Studio with sample transactions

---

**Built on GenLayer. Powered by on-chain intelligence.** 🚀
