# Social Payment App on GenLayer

A complete **GenLayer Intelligent Contract** for a decentralized social payment application.

## Features

✅ **User Profiles** – Create a username and bio  
✅ **GEN Payments** – Send native GEN to users by username  
✅ **ERC-20 Tokens** – Send any token to users by username  
✅ **Money Requests** – Request payments from other users  
✅ **Social Feed** – Post messages and content  
✅ **Post Tips** – Tip posts with GEN  
✅ **Transaction History** – Complete audit trail per user  
✅ **Follow System** – Follow and unfollow other users  

---

## What the Contract Does

This contract enables a social-first payment experience on GenLayer:

1. **Profiles** – Users register with a username (3-32 chars) and optional bio
2. **Payments** – Send funds directly to another user's username
3. **Requests** – Ask for money from friends/colleagues with a custom message
4. **Social Feed** – Post short messages (up to 1000 chars)
5. **Tipping** – Send tips to posts you like
6. **History** – View all transactions (paginated)
7. **Following** – Build a social graph

---

## File Structure

```
genlayer-social-payment-app/
├── contract/
│   └── social_payment_app.py    # Main contract code
├── README.md                     # This file
└── requirements.txt              # Python dependencies (optional)
```

---

## How to Deploy on GenLayer Studio

### 1. Open GenLayer Studio

Go to [GenLayer Studio](https://genlayer.studio) (or your local GenLayer environment)

### 2. Create a New Contract

- Click **"New Contract"**
- Select **"Python"** as the language

### 3. Copy the Contract Code

- Open `contract/social_payment_app.py`
- Copy the entire Python code
- Paste it into the GenLayer Studio editor

### 4. Compile

- Click **"Compile"**
- Fix any syntax errors if they appear

### 5. Deploy

- Click **"Deploy"**
- Approve the transaction
- Save the deployed contract address

### 6. Interact with the Contract

Use the contract address to call functions via the Studio UI or API.

---

## How to Interact with It

### 1. Create a Profile

```python
contract.create_profile(
    username="alice",
    bio="building on GenLayer"
)
```

### 2. Get Your Profile

```python
contract.get_my_profile()
# Returns: UserProfile(username="alice", bio="...", created_at="...")
```

### 3. Resolve a Username to Address

```python
contract.resolve_username("bob")
# Returns: Address("0x...")
```

### 4. Send GEN to Another User

```python
contract.send_gen(
    username="bob",
    note="Thanks for the help!"
)
```

**⚠️ Important:** Attach GEN as transaction value:
- **Studio UI:** Add value in the transaction section
- **API:** Include `value` field in the transaction

### 5. Send ERC-20 Tokens

```python
# First, approve the contract to spend your tokens:
token_contract.approve(
    spender=social_pay_address,
    amount=1000
)

# Then send:
contract.send_token(
    username="carol",
    token_address="0xYourTokenContractAddress",
    amount=1000,
    note="Payment for design"
)
```

### 6. Request Money

```python
# Request 50 GEN from dave
contract.request_money(
    username="dave",
    amount=50,
    token_address="0x0000000000000000000000000000000000000000",  # GEN
    note="Lunch today?"
)
# Returns: request_id (1, 2, 3, ...)
```

### 7. Pay a GEN Request

```python
# Dave pays the request
contract.pay_request_gen(
    request_id=1
)

# Must attach GEN value = requested amount
```

### 8. Pay a Token Request

```python
# First approve tokens, then:
contract.pay_request_token(
    request_id=2
)
```

### 9. Create a Post

```python
contract.create_post(
    content="Just deployed my first GenLayer contract!"
)
# Returns: post_id
```

### 10. Tip a Post

```python
contract.tip_post(
    post_id=1,
    note="Great work!"
)
# Attach GEN value as the tip amount
```

### 11. View Transaction History

```python
# Get transaction count
contract.get_user_transaction_count()

# Get paginated list (first 10 transactions)
contract.get_user_transactions(
    start_index=0,
    count=10
)
```

### 12. Follow a User

```python
contract.follow_user("bob")

# View followers/following
contract.get_followers()
contract.get_following()
contract.get_followers_count()
contract.get_following_count()
```

### 13. Unfollow a User

```python
contract.unfollow_user("bob")
```

### 14. Get App Info

```python
contract.get_app_info()
# Returns: "SocialPaymentApp v1.0.0"
```

---

## Example End-to-End Flow

**Scenario:** Alice sends GEN to Bob, Bob posts something, Alice tips the post

```python
# Step 1: Alice creates profile
alice.create_profile(username="alice", bio="Developer")

# Step 2: Bob creates profile
bob.create_profile(username="bob", bio="Designer")

# Step 3: Alice sends 100 GEN to Bob
alice.send_gen(
    username="bob",
    note="Payment for design work"
)  # Attach 100 GEN

# Step 4: Bob creates a post
bob_post_id = bob.create_post(content="New design system complete!")

# Step 5: Alice tips the post with 10 GEN
alice.tip_post(
    post_id=bob_post_id,
    note="Amazing!"
)  # Attach 10 GEN

# Step 6: Both can view their transaction history
alice_txns = alice.get_user_transactions(0, 10)
bob_txns = bob.get_user_transactions(0, 10)
```

---

## Data Structures

### UserProfile

```python
@dataclass
class UserProfile:
    username: str           # Username (3-32 chars, lowercase)
    bio: str               # User bio
    created_at: str        # Timestamp of creation
```

### SocialPost

```python
@dataclass
class SocialPost:
    post_id: u256          # Unique post ID
    author: Address        # Post author's wallet
    content: str           # Post content (max 1000 chars)
    created_at: str        # Creation timestamp
    tips_received: u256    # Total GEN tips received
```

### MoneyRequest

```python
@dataclass
class MoneyRequest:
    request_id: u256       # Unique request ID
    requester: Address     # Who is requesting
    payer: Address         # Who should pay
    amount: u256           # Amount to pay
    token: Address         # Token address (zero = GEN)
    note: str              # Request message
    created_at: str        # Creation timestamp
    paid: bool             # Whether it was paid
```

### TransactionRecord

```python
@dataclass
class TransactionRecord:
    transaction_id: u256   # Unique transaction ID
    sender: Address        # Sender address
    recipient: Address     # Recipient address
    amount: u256           # Amount transferred
    token: Address         # Token address (zero = GEN)
    transaction_type: str  # GEN_PAYMENT, TOKEN_PAYMENT, REQUEST_PAYMENT, POST_TIP
    reference_id: u256     # Link to request/post (if applicable)
    note: str              # Transaction note
    timestamp: str         # When it happened
    status: str            # "submitted", "finalized", etc.
```

---

## Important Notes

### Zero Address

Zero address (`0x0000000000000000000000000000000000000000`) represents **native GEN**.

Any other address is treated as an **ERC-20 token contract**.

### Case Sensitivity

Usernames are **case-insensitive** and stored in lowercase. 

- `"Alice"` and `"alice"` refer to the same profile

### Token Approvals

Before sending ERC-20 tokens, the sender must approve the contract:

```python
token.approve(social_pay_contract_address, amount)
```

### Pagination

Transaction history is paginated. Use `start_index` and `count` to fetch in batches:

```python
# Get 20 transactions, starting from index 0
contract.get_user_transactions(start_index=0, count=20)

# Get next 20
contract.get_user_transactions(start_index=20, count=20)
```

---

## Future Enhancements

Possible improvements to the contract:

- **Likes & Comments** – Extend social features
- **User Reputation** – Track trust/reputation scores
- **Feed Filtering** – Follow feed, trending posts, etc.
- **Creator Payouts** – Built-in creator monetization
- **Escrow** – Hold funds until both parties confirm
- **Dispute Resolution** – Handle payment disputes
- **Token Metadata** – Store price feeds for USD valuation
- **Premium Profiles** – Paid verification badges

---

## Testing

To test locally, use GenLayer's Python testing framework:

```python
import pytest
from social_payment_app import SocialPaymentApp

def test_create_profile():
    app = SocialPaymentApp()
    # Test implementation
    assert True
```

---

## License

MIT

---

## Support

For issues or questions:

1. Check the GenLayer documentation
2. Review the contract code comments
3. Test in GenLayer Studio with sample transactions

**Happy building! 🚀**
