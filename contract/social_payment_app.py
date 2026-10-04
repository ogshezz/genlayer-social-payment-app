# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Storage Models
# ---------------------------------------------------------------------------

@allow_storage
@dataclass
class UserProfile:
    """User profile with username and bio."""
    username: str
    bio: str
    created_at: str


@allow_storage
@dataclass
class SocialPost:
    """A post on the social feed."""
    post_id: u256
    author: Address
    content: str
    created_at: str
    tips_received: u256


@allow_storage
@dataclass
class MoneyRequest:
    """A request for payment from another user."""
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
    """Complete record of a transaction."""
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
# ERC-20 Interface
# ---------------------------------------------------------------------------

@gl.evm.contract_interface
class IERC20:
    """Standard ERC-20 token interface."""
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
    """Interface for receiving native GEN transfers."""
    class View:
        pass

    class Write:
        pass


# ---------------------------------------------------------------------------
# Social Payment Intelligent Contract
# ---------------------------------------------------------------------------

class SocialPaymentApp(gl.Contract):
    """
    Decentralized social payment application built on GenLayer.

    Features:
      - User profiles with username and bio
      - Username-based GEN and ERC-20 payments
      - Money requests between users
      - Social feed with posts and tipping
      - Complete transaction history
      - Follow/unfollow system
    """

    # -----------------------------------------------------------------------
    # Profile Storage
    # -----------------------------------------------------------------------
    
    profiles: TreeMap[Address, UserProfile]
    username_to_address: TreeMap[str, Address]

    # -----------------------------------------------------------------------
    # Social Feed Storage
    # -----------------------------------------------------------------------
    
    posts: TreeMap[u256, SocialPost]
    post_ids: DynArray[u256]

    # -----------------------------------------------------------------------
    # Money Request Storage
    # -----------------------------------------------------------------------
    
    requests: TreeMap[u256, MoneyRequest]
    request_ids: DynArray[u256]

    # -----------------------------------------------------------------------
    # Transaction History Storage
    # -----------------------------------------------------------------------
    
    transactions: TreeMap[u256, TransactionRecord]
    transaction_ids: DynArray[u256]
    user_transaction_ids: TreeMap[Address, DynArray[u256]]

    # -----------------------------------------------------------------------
    # Follow System Storage
    # -----------------------------------------------------------------------
    
    following: TreeMap[Address, DynArray[Address]]
    followers: TreeMap[Address, DynArray[Address]]

    # -----------------------------------------------------------------------
    # ID Counters
    # -----------------------------------------------------------------------
    
    next_post_id: u256
    next_request_id: u256
    next_transaction_id: u256

    # -----------------------------------------------------------------------
    # Metadata
    # -----------------------------------------------------------------------
    
    app_name: str
    version: str

    def __init__(self) -> None:
        """
        Initialize the SocialPaymentApp contract.
        Storage maps are automatically initialized by GenLayer.
        """
        self.app_name = "SocialPaymentApp"
        self.version = "1.1.0"
        self.next_post_id = u256(1)
        self.next_request_id = u256(1)
        self.next_transaction_id = u256(1)

    # =======================================================================
    # Internal Helpers
    # =======================================================================

    def _timestamp(self) -> str:
        """Get current timestamp from GenLayer runtime."""
        return gl.message_raw["datetime"]

    def _zero_address(self) -> Address:
        """Return zero address constant."""
        return Address("0x0000000000000000000000000000000000000000")

    def _normalize_username(self, username: str) -> str:
        """Normalize username to lowercase for consistent lookups."""
        return username.strip().lower()

    def _validate_username(self, username: str) -> str:
        """
        Validate username format and return normalized version.
        Rules:
          - Minimum 3 characters
          - Maximum 32 characters
          - Alphanumeric and underscore only
        """
        normalized = self._normalize_username(username)
        
        if len(normalized) < 3:
            raise gl.vm.UserError("Username must be at least 3 characters")
        
        if len(normalized) > 32:
            raise gl.vm.UserError("Username must be 32 characters or less")
        
        # Validate characters: only alphanumeric and underscore
        for char in normalized:
            if not (char.isalnum() or char == '_'):
                raise gl.vm.UserError("Username can only contain letters, numbers, and underscores")
        
        return normalized

    def _validate_bio(self, bio: str) -> None:
        """Validate bio length (max 500 chars)."""
        if len(bio) > 500:
            raise gl.vm.UserError("Bio must be 500 characters or less")

    def _validate_post_content(self, content: str) -> None:
        """Validate post content length (max 1000 chars)."""
        if len(content) == 0:
            raise gl.vm.UserError("Post cannot be empty")
        
        if len(content) > 1000:
            raise gl.vm.UserError("Post is too long (max 1000 characters)")

    def _require_profile(self, user: Address) -> None:
        """Revert if user does not have a profile."""
        profile = self.profiles.get(user, UserProfile("", "", ""))
        
        if profile.username == "":
            raise gl.vm.UserError("User profile does not exist")

    def _resolve_username(self, username: str) -> Address:
        """
        Convert a username to an address.
        Raises UserError if username does not exist.
        """
        normalized = self._normalize_username(username)
        zero = self._zero_address()
        address = self.username_to_address.get(normalized, zero)
        
        if address == zero:
            raise gl.vm.UserError("Username does not exist")
        
        return address

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
        """
        Record a transaction and index it for both sender and recipient.
        Returns transaction_id.
        """
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
        
        # Index for sender
        sender_history = self.user_transaction_ids[sender]
        sender_history.append(tx_id)
        self.user_transaction_ids[sender] = sender_history
        
        # Index for recipient
        recipient_history = self.user_transaction_ids[recipient]
        recipient_history.append(tx_id)
        self.user_transaction_ids[recipient] = recipient_history
        
        self.next_transaction_id = tx_id + u256(1)
        
        return tx_id

    def _send_native_gen(self, recipient: Address, amount: u256) -> None:
        """
        Queue a native GEN transfer via finalized external message.
        """
        if amount == u256(0):
            raise gl.vm.UserError("Amount must be greater than zero")
        
        NativeTransferReceiver(recipient).emit_transfer(value=amount)

    def _send_erc20_token(
        self,
        token: Address,
        sender: Address,
        recipient: Address,
        amount: u256,
    ) -> None:
        """
        Transfer an ERC-20 token using transferFrom.
        Sender must have approved this contract beforehand.
        """
        if amount == u256(0):
            raise gl.vm.UserError("Amount must be greater than zero")
        
        if token == self._zero_address():
            raise gl.vm.UserError("Invalid token address")
        
        IERC20(token).emit(on="finalized").transfer_from(sender, recipient, amount)

    # =======================================================================
    # Profile Management
    # =======================================================================

    @gl.public.write
    def create_profile(self, username: str, bio: str) -> None:
        """
        Create a user profile.
        
        Args:
            username: Desired username (3-32 characters, alphanumeric + underscore)
            bio: User bio (max 500 characters)
        """
        caller = gl.message.sender_address
        normalized = self._validate_username(username)
        self._validate_bio(bio)
        
        # Check if profile already exists
        existing = self.profiles.get(caller, UserProfile("", "", ""))
        if existing.username != "":
            raise gl.vm.UserError("Profile already exists")
        
        # Check if username is taken
        if self.username_to_address.get(normalized, self._zero_address()) != self._zero_address():
            raise gl.vm.UserError("Username is already taken")
        
        # Create profile
        self.profiles[caller] = UserProfile(
            username=normalized,
            bio=bio,
            created_at=self._timestamp(),
        )
        
        self.username_to_address[normalized] = caller

    @gl.public.write
    def update_profile(self, bio: str) -> None:
        """
        Update the caller's bio.
        
        Args:
            bio: New bio (max 500 characters)
        """
        caller = gl.message.sender_address
        self._require_profile(caller)
        self._validate_bio(bio)
        
        profile = self.profiles[caller]
        self.profiles[caller] = UserProfile(
            username=profile.username,
            bio=bio,
            created_at=profile.created_at,
        )

    @gl.public.view
    def get_profile(self, username: str) -> UserProfile:
        """Get a profile by username."""
        address = self._resolve_username(username)
        return self.profiles[address]

    @gl.public.view
    def get_my_profile(self) -> UserProfile:
        """Get the caller's own profile."""
        caller = gl.message.sender_address
        self._require_profile(caller)
        return self.profiles[caller]

    @gl.public.view
    def resolve_username(self, username: str) -> Address:
        """Resolve a username to its wallet address."""
        return self._resolve_username(username)

    # =======================================================================
    # GEN Payments
    # =======================================================================

    @gl.public.write.payable
    def send_gen(self, username: str, note: str) -> None:
        """
        Send native GEN to another user by username.
        
        Args:
            username: Recipient's username
            note: Payment note/memo
            
        GEN amount is sent as transaction value.
        """
        sender = gl.message.sender_address
        recipient = self._resolve_username(username)
        amount = gl.message.value
        
        self._require_profile(sender)
        
        if amount == u256(0):
            raise gl.vm.UserError("Attach some GEN to the transaction")
        
        if recipient == sender:
            raise gl.vm.UserError("Cannot send GEN to yourself")
        
        self._record_transaction(
            sender=sender,
            recipient=recipient,
            amount=amount,
            token=self._zero_address(),
            transaction_type="GEN_PAYMENT",
            reference_id=u256(0),
            note=note,
        )
        
        self._send_native_gen(recipient, amount)

    # =======================================================================
    # ERC-20 Token Payments
    # =======================================================================

    @gl.public.write
    def send_token(
        self,
        username: str,
        token_address: str,
        amount: u256,
        note: str,
    ) -> None:
        """
        Send ERC-20 tokens to another user by username.
        
        Args:
            username: Recipient's username
            token_address: ERC-20 contract address
            amount: Amount to transfer
            note: Payment note/memo
            
        Sender must have approved this contract beforehand.
        """
        sender = gl.message.sender_address
        recipient = self._resolve_username(username)
        token = Address(token_address)
        
        self._require_profile(sender)
        
        if amount == u256(0):
            raise gl.vm.UserError("Amount must be greater than zero")
        
        if recipient == sender:
            raise gl.vm.UserError("Cannot send tokens to yourself")
        
        self._record_transaction(
            sender=sender,
            recipient=recipient,
            amount=amount,
            token=token,
            transaction_type="TOKEN_PAYMENT",
            reference_id=u256(0),
            note=note,
        )
        
        self._send_erc20_token(token, sender, recipient, amount)

    # =======================================================================
    # Money Requests
    # =======================================================================

    @gl.public.write
    def request_money(
        self,
        username: str,
        amount: u256,
        token_address: str,
        note: str,
    ) -> u256:
        """
        Create a payment request from another user.
        
        Args:
            username: Username of the payer
            amount: Requested amount
            token_address: Token address (zero address = GEN)
            note: Request message
            
        Returns:
            request_id of the created request
        """
        requester = gl.message.sender_address
        payer = self._resolve_username(username)
        token = Address(token_address)
        
        self._require_profile(requester)
        
        if amount == u256(0):
            raise gl.vm.UserError("Requested amount must be greater than zero")
        
        if requester == payer:
            raise gl.vm.UserError("Cannot request money from yourself")
        
        request_id = self.next_request_id
        self.requests[request_id] = MoneyRequest(
            request_id=request_id,
            requester=requester,
            payer=payer,
            amount=amount,
            token=token,
            note=note,
            created_at=self._timestamp(),
            paid=False,
        )
        self.request_ids.append(request_id)
        self.next_request_id = request_id + u256(1)
        
        return request_id

    @gl.public.view
    def get_request(self, request_id: u256) -> MoneyRequest:
        """Get a money request by ID."""
        return self.requests[request_id]

    @gl.public.write.payable
    def pay_request_gen(self, request_id: u256) -> None:
        """
        Pay a GEN-denominated money request.
        
        Args:
            request_id: ID of the request to pay
            
        Caller must attach GEN equal to the request amount.
        """
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
        
        # Create updated record with paid=True
        paid_request = MoneyRequest(
            request_id=request.request_id,
            requester=request.requester,
            payer=request.payer,
            amount=request.amount,
            token=request.token,
            note=request.note,
            created_at=request.created_at,
            paid=True,
        )
        self.requests[request_id] = paid_request
        
        self._record_transaction(
            sender=payer,
            recipient=request.requester,
            amount=request.amount,
            token=self._zero_address(),
            transaction_type="REQUEST_PAYMENT",
            reference_id=request_id,
            note=request.note,
        )
        
        self._send_native_gen(request.requester, request.amount)

    @gl.public.write
    def pay_request_token(self, request_id: u256) -> None:
        """
        Pay an ERC-20 token-denominated money request.
        
        Args:
            request_id: ID of the request to pay
            
        Caller must have approved the token transfer beforehand.
        """
        payer = gl.message.sender_address
        request = self.requests[request_id]
        
        if request.paid:
            raise gl.vm.UserError("Request already paid")
        
        if request.payer != payer:
            raise gl.vm.UserError("You are not the payer for this request")
        
        if request.token == self._zero_address():
            raise gl.vm.UserError("This request is for native GEN, not a token")
        
        # Create updated record with paid=True
        paid_request = MoneyRequest(
            request_id=request.request_id,
            requester=request.requester,
            payer=request.payer,
            amount=request.amount,
            token=request.token,
            note=request.note,
            created_at=request.created_at,
            paid=True,
        )
        self.requests[request_id] = paid_request
        
        self._record_transaction(
            sender=payer,
            recipient=request.requester,
            amount=request.amount,
            token=request.token,
            transaction_type="REQUEST_PAYMENT",
            reference_id=request_id,
            note=request.note,
        )
        
        self._send_erc20_token(request.token, payer, request.requester, request.amount)

    # =======================================================================
    # Social Feed
    # =======================================================================

    @gl.public.write
    def create_post(self, content: str) -> u256:
        """
        Create a social feed post.
        
        Args:
            content: Post content (max 1000 characters)
            
        Returns:
            post_id of the created post
        """
        author = gl.message.sender_address
        self._require_profile(author)
        self._validate_post_content(content)
        
        post_id = self.next_post_id
        self.posts[post_id] = SocialPost(
            post_id=post_id,
            author=author,
            content=content,
            created_at=self._timestamp(),
            tips_received=u256(0),
        )
        self.post_ids.append(post_id)
        self.next_post_id = post_id + u256(1)
        
        return post_id

    @gl.public.view
    def get_post(self, post_id: u256) -> SocialPost:
        """Get a single post by ID."""
        return self.posts[post_id]

    @gl.public.view
    def get_post_count(self) -> u256:
        """Get total number of posts created."""
        return u256(len(self.post_ids))

    @gl.public.write.payable
    def tip_post(self, post_id: u256, note: str) -> None:
        """
        Tip a post author with native GEN.
        
        Args:
            post_id: ID of the post to tip
            note: Tip message/memo
            
        GEN amount is sent as transaction value.
        """
        tipper = gl.message.sender_address
        amount = gl.message.value
        
        self._require_profile(tipper)
        
        post = self.posts[post_id]
        
        if amount == u256(0):
            raise gl.vm.UserError("Attach some GEN to tip the post")
        
        if post.author == tipper:
            raise gl.vm.UserError("Cannot tip your own post")
        
        # Create updated post with new tips_received value
        updated_post = SocialPost(
            post_id=post.post_id,
            author=post.author,
            content=post.content,
            created_at=post.created_at,
            tips_received=post.tips_received + amount,
        )
        self.posts[post_id] = updated_post
        
        self._record_transaction(
            sender=tipper,
            recipient=post.author,
            amount=amount,
            token=self._zero_address(),
            transaction_type="POST_TIP",
            reference_id=post_id,
            note=note,
        )
        
        self._send_native_gen(post.author, amount)

    # =======================================================================
    # Transaction History
    # =======================================================================

    @gl.public.view
    def get_transaction(self, transaction_id: u256) -> TransactionRecord:
        """Get a transaction by ID."""
        return self.transactions[transaction_id]

    @gl.public.view
    def get_user_transaction_count(self) -> u256:
        """Get total number of transactions for the caller."""
        caller = gl.message.sender_address
        return u256(len(self.user_transaction_ids[caller]))

    @gl.public.view
    def get_user_transactions(self, start_index: u256, count: u256) -> DynArray[TransactionRecord]:
        """
        Get a paginated list of transactions for the caller.
        
        Args:
            start_index: Starting index in the transaction list
            count: Number of transactions to fetch
            
        Returns:
            List of transactions
        """
        caller = gl.message.sender_address
        tx_ids = self.user_transaction_ids[caller]
        
        # Build result using proper DynArray initialization
        results: DynArray[TransactionRecord] = []
        end_index = start_index + count
        
        i: u256 = start_index
        while i < end_index and i < u256(len(tx_ids)):
            tx_id = tx_ids[i]
            results.append(self.transactions[tx_id])
            i = i + u256(1)
        
        return results

    # =======================================================================
    # Follow System
    # =======================================================================

    @gl.public.write
    def follow_user(self, username: str) -> None:
        """
        Follow another user.
        
        Args:
            username: Username to follow
        """
        follower = gl.message.sender_address
        followed = self._resolve_username(username)
        
        self._require_profile(follower)
        self._require_profile(followed)
        
        if follower == followed:
            raise gl.vm.UserError("Cannot follow yourself")
        
        # Check if already following
        following_list = self.following[follower]
        i: u256 = 0
        while i < u256(len(following_list)):
            if following_list[i] == followed:
                raise gl.vm.UserError("Already following this user")
            i = i + u256(1)
        
        following_list.append(followed)
        self.following[follower] = following_list
        
        followers_list = self.followers[followed]
        followers_list.append(follower)
        self.followers[followed] = followers_list

    @gl.public.write
    def unfollow_user(self, username: str) -> None:
        """
        Unfollow a user.
        
        Args:
            username: Username to unfollow
        """
        follower = gl.message.sender_address
        followed = self._resolve_username(username)
        
        # Remove from following list using safer pattern
        current_following = self.following[follower]
        new_following: DynArray[Address] = []
        
        i: u256 = 0
        while i < u256(len(current_following)):
            if current_following[i] != followed:
                new_following.append(current_following[i])
            i = i + u256(1)
        
        self.following[follower] = new_following
        
        # Remove from followers list using safer pattern
        current_followers = self.followers[followed]
        new_followers: DynArray[Address] = []
        
        j: u256 = 0
        while j < u256(len(current_followers)):
            if current_followers[j] != follower:
                new_followers.append(current_followers[j])
            j = j + u256(1)
        
        self.followers[followed] = new_followers

    @gl.public.view
    def get_following(self) -> DynArray[Address]:
        """Get list of addresses the caller is following."""
        caller = gl.message.sender_address
        return self.following[caller]

    @gl.public.view
    def get_followers(self) -> DynArray[Address]:
        """Get list of addresses following the caller."""
        caller = gl.message.sender_address
        return self.followers[caller]

    @gl.public.view
    def get_following_count(self) -> u256:
        """Get number of users the caller is following."""
        caller = gl.message.sender_address
        return u256(len(self.following[caller]))

    @gl.public.view
    def get_followers_count(self) -> u256:
        """Get number of followers the caller has."""
        caller = gl.message.sender_address
        return u256(len(self.followers[caller]))

    # =======================================================================
    # Contract Info
    # =======================================================================

    @gl.public.view
    def get_app_info(self) -> str:
        """Get app name and version."""
        return f"{self.app_name} v{self.version}"
