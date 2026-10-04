from dataclasses import dataclass
from genlayer import *

# ---------------------------------------------------------------------------
# Storage models
# ---------------------------------------------------------------------------

@allow_storage
@dataclass
class UserProfile:
    username: str
    bio: str
    created_at: str


@allow_storage
@dataclass
class SocialPost:
    post_id: u256
    author: Address
    content: str
    created_at: str
    tips_received: u256


@allow_storage
@dataclass
class MoneyRequest:
    request_id: u256
    requester: Address
    payer: Address
    amount: u256
    token: Address
    note: str
    created_at: str
    paid: bool


@allow_storage
@dataclass
class TransactionRecord:
    transaction_id: u256
    sender: Address
    recipient: Address
    amount: u256
    token: Address
    transaction_type: str
    reference_id: u256
    note: str
    timestamp: str
    status: str


# ---------------------------------------------------------------------------
# ERC-20 interface
# ---------------------------------------------------------------------------

@gl.evm.contract_interface
class IERC20:
    class View:
        def balance_of(self, owner: Address) -> u256: ...

    class Write:
        def transfer(self, to: Address, amount: u256) -> bool: ...
        def transfer_from(
            self,
            from_address: Address,
            to: Address,
            amount: u256,
        ) -> bool: ...


@gl.evm.contract_interface
class NativeTransferReceiver:
    class View:
        pass

    class Write:
        pass


# ---------------------------------------------------------------------------
# Social Payment Intelligent Contract
# ---------------------------------------------------------------------------

class SocialPaymentApp(gl.Contract):
    """
    A social payment app on GenLayer.

    Features:
    - User profiles with username + bio
    - Username-based payment sends (GEN or ERC-20)
    - Money request support
    - Social feed with posts
    - Tips on posts
    - Transaction history per user
    - Follow / unfollow system
    """

    # Users
    profiles: TreeMap[Address, UserProfile]
    username_to_address: TreeMap[str, Address]

    # Posts
    posts: TreeMap[u256, SocialPost]
    post_ids: DynArray[u256]

    # Requests
    requests: TreeMap[u256, MoneyRequest]
    request_ids: DynArray[u256]

    # Transactions
    transactions: TreeMap[u256, TransactionRecord]
    transaction_ids: DynArray[u256]
    user_transaction_ids: TreeMap[Address, DynArray[u256]]

    # Social graph
    following: TreeMap[Address, DynArray[Address]]
    followers: TreeMap[Address, DynArray[Address]]

    # Next IDs
    next_post_id: u256
    next_request_id: u256
    next_transaction_id: u256

    # Metadata
    app_name: str
    version: str

    def __init__(self) -> None:
        """Initialize the app state."""
        self.app_name = "SocialPaymentApp"
        self.version = "1.0.0"
        self.next_post_id = u256(1)
        self.next_request_id = u256(1)
        self.next_transaction_id = u256(1)

    # -----------------------------------------------------------------------
    # Utility helpers
    # -----------------------------------------------------------------------

    def _timestamp(self) -> str:
        """Return current timestamp from GenLayer."""
        return gl.message_raw["datetime"]

    def _normalize_username(self, username: str) -> str:
        """Normalize username for case-insensitive lookups."""
        return username.strip().lower()

    def _require_profile(self, user: Address) -> None:
        """Ensure a profile exists."""
        profile = self.profiles.get(user, UserProfile("", "", ""))
        if profile.username == "":
            raise gl.vm.UserError("User profile does not exist")

    def _require_valid_username(self, username: str) -> str:
        """Validate username (3-32 chars)."""
        normalized = self._normalize_username(username)
        if len(normalized) < 3:
            raise gl.vm.UserError("Username must be at least 3 characters")
        if len(normalized) > 32:
            raise gl.vm.UserError("Username must be 32 characters or less")
        return normalized

    def _resolve_username(self, username: str) -> Address:
        """Convert username to address."""
        normalized = self._normalize_username(username)
        zero = Address("0x0000000000000000000000000000000000000000")
        target = self.username_to_address.get(normalized, zero)
        if target == zero:
            raise gl.vm.UserError("Username does not exist")
        return target

    def _zero_address(self) -> Address:
        return Address("0x0000000000000000000000000000000000000000")

    def _record_transaction(
        self,
        sender: Address,
        recipient: Address,
        amount: u256,
        token: Address,
        transaction_type: str,
        reference_id: u256,
        note: str,
    ) -> u256:
        """Record a transaction in both sender and recipient histories."""
        tx_id = self.next_transaction_id
        record = TransactionRecord(
            transaction_id=tx_id,
            sender=sender,
            recipient=recipient,
            amount=amount,
            token=token,
            transaction_type=transaction_type,
            reference_id=reference_id,
            note=note,
            timestamp=self._timestamp(),
            status="submitted",
        )
        self.transactions[tx_id] = record
        self.transaction_ids.append(tx_id)
        sender_list = self.user_transaction_ids[sender]
        sender_list.append(tx_id)
        self.user_transaction_ids[sender] = sender_list
        recipient_list = self.user_transaction_ids[recipient]
        recipient_list.append(tx_id)
        self.user_transaction_ids[recipient] = recipient_list
        self.next_transaction_id = tx_id + u256(1)
        return tx_id

    def _send_native_gen(self, recipient: Address, amount: u256) -> None:
        """Send native GEN to another address."""
        if amount == u256(0):
            raise gl.vm.UserError("Amount must be greater than zero")
        NativeTransferReceiver(recipient).emit_transfer(value=amount)

    def _send_token(self, token: Address, sender: Address, recipient: Address, amount: u256) -> None:
        """Transfer ERC-20 tokens using transferFrom."""
        if amount == u256(0):
            raise gl.vm.UserError("Amount must be greater than zero")
        IERC20(token).emit(on="finalized").transfer_from(sender, recipient, amount)

    # -----------------------------------------------------------------------
    # Profile functions
    # -----------------------------------------------------------------------

    @gl.public.write
    def create_profile(self, username: str, bio: str) -> None:
        """Create a profile for the caller."""
        caller = gl.message.sender_address
        normalized = self._require_valid_username(username)
        existing = self.profiles.get(caller, UserProfile("", "", ""))
        if existing.username != "":
            raise gl.vm.UserError("Profile already exists")
        owner = self.username_to_address.get(normalized, self._zero_address())
        if owner != self._zero_address():
            raise gl.vm.UserError("Username is already taken")
        self.profiles[caller] = UserProfile(username=normalized, bio=bio, created_at=self._timestamp())
        self.username_to_address[normalized] = caller

    @gl.public.write
    def update_profile(self, bio: str) -> None:
        """Update the caller's bio."""
        caller = gl.message.sender_address
        self._require_profile(caller)
        profile = self.profiles[caller]
        self.profiles[caller] = UserProfile(username=profile.username, bio=bio, created_at=profile.created_at)

    @gl.public.view
    def get_profile(self, username: str) -> UserProfile:
        """Fetch a profile by username."""
        address = self._resolve_username(username)
        return self.profiles[address]

    @gl.public.view
    def get_my_profile(self) -> UserProfile:
        """Fetch the current caller's profile."""
        caller = gl.message.sender_address
        self._require_profile(caller)
        return self.profiles[caller]

    @gl.public.view
    def resolve_username(self, username: str) -> Address:
        """Resolve a username to an address."""
        return self._resolve_username(username)

    # -----------------------------------------------------------------------
    # Payments: native GEN
    # -----------------------------------------------------------------------

    @gl.public.write.payable
    def send_gen(self, username: str, note: str) -> None:
        """Send native GEN to another user using their username."""
        sender = gl.message.sender_address
        recipient = self._resolve_username(username)
        amount = gl.message.value
        self._require_profile(sender)
        if amount == u256(0):
            raise gl.vm.UserError("Attach some GEN to the transaction")
        if recipient == sender:
            raise gl.vm.UserError("Cannot send GEN to yourself")
        self._record_transaction(sender=sender, recipient=recipient, amount=amount, token=self._zero_address(),
            transaction_type="GEN_PAYMENT", reference_id=u256(0), note=note)
        self._send_native_gen(recipient, amount)

    # -----------------------------------------------------------------------
    # Payments: ERC-20 tokens
    # -----------------------------------------------------------------------

    @gl.public.write
    def send_token(self, username: str, token_address: str, amount: u256, note: str) -> None:
        """Send ERC-20 tokens to a user identified by username."""
        sender = gl.message.sender_address
        recipient = self._resolve_username(username)
        token = Address(token_address)
        self._require_profile(sender)
        if amount == u256(0):
            raise gl.vm.UserError("Amount must be greater than zero")
        if recipient == sender:
            raise gl.vm.UserError("Cannot send tokens to yourself")
        self._record_transaction(sender=sender, recipient=recipient, amount=amount, token=token,
            transaction_type="TOKEN_PAYMENT", reference_id=u256(0), note=note)
        self._send_token(token, sender, recipient, amount)

    # -----------------------------------------------------------------------
    # Money request functions
    # -----------------------------------------------------------------------

    @gl.public.write
    def request_money(self, username: str, amount: u256, token_address: str, note: str) -> u256:
        """Request money from another user."""
        requester = gl.message.sender_address
        payer = self._resolve_username(username)
        token = Address(token_address)
        self._require_profile(requester)
        if amount == u256(0):
            raise gl.vm.UserError("Requested amount must be greater than zero")
        if requester == payer:
            raise gl.vm.UserError("Cannot request money from yourself")
        request_id = self.next_request_id
        self.requests[request_id] = MoneyRequest(request_id=request_id, requester=requester, payer=payer,
            amount=amount, token=token, note=note, created_at=self._timestamp(), paid=False)
        self.request_ids.append(request_id)
        self.next_request_id = request_id + u256(1)
        return request_id

    @gl.public.view
    def get_request(self, request_id: u256) -> MoneyRequest:
        """Fetch a request by ID."""
        return self.requests[request_id]

    @gl.public.write.payable
    def pay_request_gen(self, request_id: u256) -> None:
        """Pay a GEN money request."""
        payer = gl.message.sender_address
        request = self.requests[request_id]
        if request.paid:
            raise gl.vm.UserError("Request already paid")
        if request.payer != payer:
            raise gl.vm.UserError("You are not the payer for this request")
        if request.token != self._zero_address():
            raise gl.vm.UserError("This request is for an ERC-20 token, not GEN")
        if gl.message.value != request.amount:
            raise gl.vm.UserError("Attached GEN does not match request amount")
        request.paid = True
        self.requests[request_id] = request
        self._record_transaction(sender=payer, recipient=request.requester, amount=request.amount,
            token=self._zero_address(), transaction_type="REQUEST_PAYMENT", reference_id=request_id, note=request.note)
        self._send_native_gen(request.requester, request.amount)

    @gl.public.write
    def pay_request_token(self, request_id: u256) -> None:
        """Pay an ERC-20 token money request."""
        payer = gl.message.sender_address
        request = self.requests[request_id]
        if request.paid:
            raise gl.vm.UserError("Request already paid")
        if request.payer != payer:
            raise gl.vm.UserError("You are not the payer for this request")
        if request.token == self._zero_address():
            raise gl.vm.UserError("This request is for native GEN, not a token")
        request.paid = True
        self.requests[request_id] = request
        self._record_transaction(sender=payer, recipient=request.requester, amount=request.amount, token=request.token,
            transaction_type="REQUEST_PAYMENT", reference_id=request_id, note=request.note)
        self._send_token(request.token, payer, request.requester, request.amount)

    # -----------------------------------------------------------------------
    # Social feed
    # -----------------------------------------------------------------------

    @gl.public.write
    def create_post(self, content: str) -> u256:
        """Create a social feed post."""
        author = gl.message.sender_address
        self._require_profile(author)
        if len(content) == 0:
            raise gl.vm.UserError("Post cannot be empty")
        if len(content) > 1000:
            raise gl.vm.UserError("Post is too long")
        post_id = self.next_post_id
        self.posts[post_id] = SocialPost(post_id=post_id, author=author, content=content,
            created_at=self._timestamp(), tips_received=u256(0))
        self.post_ids.append(post_id)
        self.next_post_id = post_id + u256(1)
        return post_id

    @gl.public.view
    def get_post(self, post_id: u256) -> SocialPost:
        """Fetch a single post."""
        return self.posts[post_id]

    @gl.public.view
    def get_post_count(self) -> u256:
        """Return total number of posts."""
        return u256(len(self.post_ids))

    @gl.public.write.payable
    def tip_post(self, post_id: u256, note: str) -> None:
        """Send native GEN as a tip to a post author."""
        tipper = gl.message.sender_address
        amount = gl.message.value
        self._require_profile(tipper)
        post = self.posts[post_id]
        if amount == u256(0):
            raise gl.vm.UserError("Attach some GEN to tip the post")
        if post.author == tipper:
            raise gl.vm.UserError("Cannot tip your own post")
        post.tips_received = post.tips_received + amount
        self.posts[post_id] = post
        self._record_transaction(sender=tipper, recipient=post.author, amount=amount,
            token=self._zero_address(), transaction_type="POST_TIP", reference_id=post_id, note=note)
        self._send_native_gen(post.author, amount)

    # -----------------------------------------------------------------------
    # Transaction history
    # -----------------------------------------------------------------------

    @gl.public.view
    def get_transaction(self, transaction_id: u256) -> TransactionRecord:
        """Fetch a specific transaction."""
        return self.transactions[transaction_id]

    @gl.public.view
    def get_user_transaction_count(self) -> u256:
        """Return the number of transactions for the caller."""
        caller = gl.message.sender_address
        return u256(len(self.user_transaction_ids[caller]))

    @gl.public.view
    def get_user_transactions(self, start_index: u256, count: u256) -> DynArray[TransactionRecord]:
        """Fetch a paginated list of transactions for the caller."""
        caller = gl.message.sender_address
        tx_ids = self.user_transaction_ids[caller]
        results: DynArray[TransactionRecord] = []
        end_index = start_index + count
        i: u256 = start_index
        while i < end_index and i < u256(len(tx_ids)):
            tx_id = tx_ids[i]
            results.append(self.transactions[tx_id])
            i = i + u256(1)
        return results

    # -----------------------------------------------------------------------
    # Follow system
    # -----------------------------------------------------------------------

    @gl.public.write
    def follow_user(self, username: str) -> None:
        """Follow another user."""
        follower = gl.message.sender_address
        followed = self._resolve_username(username)
        self._require_profile(follower)
        self._require_profile(followed)
        if follower == followed:
            raise gl.vm.UserError("Cannot follow yourself")
        current_following = self.following[follower]
        i: u256 = 0
        while i < u256(len(current_following)):
            if current_following[i] == followed:
                raise gl.vm.UserError("Already following this user")
            i = i + u256(1)
        current_following.append(followed)
        self.following[follower] = current_following
        current_followers = self.followers[followed]
        current_followers.append(follower)
        self.followers[followed] = current_followers

    @gl.public.write
    def unfollow_user(self, username: str) -> None:
        """Unfollow a user."""
        follower = gl.message.sender_address
        followed = self._resolve_username(username)
        new_following: DynArray[Address] = []
        current_following = self.following[follower]
        i: u256 = 0
        while i < u256(len(current_following)):
            if current_following[i] != followed:
                new_following.append(current_following[i])
            i = i + u256(1)
        self.following[follower] = new_following
        new_followers: DynArray[Address] = []
        current_followers = self.followers[followed]
        j: u256 = 0
        while j < u256(len(current_followers)):
            if current_followers[j] != follower:
                new_followers.append(current_followers[j])
            j = j + u256(1)
        self.followers[followed] = new_followers

    @gl.public.view
    def get_following(self) -> DynArray[Address]:
        """Return addresses this user is following."""
        caller = gl.message.sender_address
        return self.following[caller]

    @gl.public.view
    def get_followers(self) -> DynArray[Address]:
        """Return addresses following this user."""
        caller = gl.message.sender_address
        return self.followers[caller]

    @gl.public.view
    def get_following_count(self) -> u256:
        """Return number of followings for caller."""
        caller = gl.message.sender_address
        return u256(len(self.following[caller]))

    @gl.public.view
    def get_followers_count(self) -> u256:
        """Return number of followers for caller."""
        caller = gl.message.sender_address
        return u256(len(self.followers[caller]))

    @gl.public.view
    def get_app_info(self) -> str:
        """Return simple app metadata."""
        return f"{self.app_name} v{self.version}"
