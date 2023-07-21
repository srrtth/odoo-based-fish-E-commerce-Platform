from odoo import models, fields, api

class Fish(models.Model):
    _name = 'fish.fish'
    _description = 'Fish Product'

    name = fields.Char(string='Fish Name', required=True)
    species = fields.Char(string='Species', required=True)
    size = fields.Float(string='Size', required=True)
    price = fields.Float(string='Price', required=True)
    description = fields.Text(string='Description')
    image = fields.Binary(string='Image', attachment=True)
    stock_qty = fields.Float(string='Stock Quantity', default=0)
    is_available = fields.Boolean(string='Is Available', compute='_compute_availability')
    rating = fields.Float(string='Rating', compute='_compute_rating', store=True)
    review_ids = fields.One2many('fish.review', 'fish_id', string='Reviews')
    num_reviews = fields.Integer(string='Number of Reviews', compute='_compute_num_reviews')

    @api.depends('stock_qty')
    def _compute_availability(self):
        for fish in self:
            fish.is_available = fish.stock_qty > 0

    @api.depends('review_ids.rating')
    def _compute_rating(self):
        for fish in self:
            if fish.review_ids:
                fish.rating = sum(review.rating for review in fish.review_ids) / len(fish.review_ids)
            else:
                fish.rating = 0.0

    @api.depends('review_ids')
    def _compute_num_reviews(self):
        for fish in self:
            fish.num_reviews = len(fish.review_ids)

class FishReview(models.Model):
    _name = 'fish.review'
    _description = 'Fish Review'

    user_id = fields.Many2one('res.users', string='User', required=True)
    fish_id = fields.Many2one('fish.fish', string='Fish', required=True)
    rating = fields.Float(string='Rating', required=True)
    comment = fields.Text(string='Comment')
    review_date = fields.Datetime(string='Review Date', default=fields.Datetime.now)

class UserFavorite(models.Model):
    _name = 'user.favorite'
    _description = 'User Favorite'

    user_id = fields.Many2one('res.users', string='User', required=True)
    fish_id = fields.Many2one('fish.fish', string='Fish', required=True)

class FishCategory(models.Model):
    _name = 'fish.category'
    _description = 'Fish Category'

    name = fields.Char(string='Category Name', required=True)
    description = fields.Text(string='Description')
    fish_ids = fields.Many2many('fish.fish', string='Fishes')

class UserNotification(models.Model):
    _name = 'user.notification'
    _description = 'User Notification'
    _rec_name = 'title'

    user_id = fields.Many2one('res.users', string='User', required=True)
    title = fields.Char(string='Title', required=True)
    message = fields.Text(string='Message')
    is_read = fields.Boolean(string='Is Read', default=False)

class FishECommerce(models.Model):
    _name = 'fish.ecommerce'
    _description = 'Fish E-commerce Platform'

    name = fields.Char(string='Name', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    fish_ids = fields.Many2many('fish.fish', string='Available Fishes')
    category_ids = fields.Many2many('fish.category', string='Fish Categories')

    @api.depends('fish_ids.stock_qty')
    def _compute_available_fish_count(self):
        for platform in self:
            platform.available_fish_count = len(platform.fish_ids.filtered(lambda fish: fish.is_available))

    available_fish_count = fields.Integer(string='Available Fishes', compute='_compute_available_fish_count')

    def get_popular_fishes(self, limit=10):
        return self.fish_ids.sorted(key=lambda fish: fish.num_reviews, reverse=True)[:limit]

    def get_newly_added_fishes(self, limit=10):
        return self.fish_ids.sorted(key=lambda fish: fish.create_date, reverse=True)[:limit]

class ShoppingCart(models.Model):
    _name = 'shopping.cart'
    _description = 'Shopping Cart'

    user_id = fields.Many2one('res.users', string='User', required=True)
    cart_items = fields.Many2many('fish.fish', string='Cart Items')
    total_price = fields.Float(string='Total Price', compute='_compute_total_price')

    @api.depends('cart_items.price')
    def _compute_total_price(self):
        for cart in self:
            cart.total_price = sum(item.price for item in cart.cart_items)

    def action_empty_cart(self):
        # Empty the shopping cart by removing all cart items
        self.cart_items = [(5, 0, 0)]

class Order(models.Model):
    _name = 'order'
    _description = 'Order'

    user_id = fields.Many2one('res.users', string='User', required=True)
    order_lines = fields.One2many('order.line', 'order_id', string='Order Lines')
    total_price = fields.Float(string='Total Price', compute='_compute_total_price')
    order_date = fields.Datetime(string='Order Date', default=fields.Datetime.now)

    @api.depends('order_lines.price')
    def _compute_total_price(self):
        for order in self:
            order.total_price = sum(line.price for line in order.order_lines)

    def action_confirm_order(self):
        # Set the order status as 'Confirmed' and update stock quantities
        self.state = 'confirmed'
        for line in self.order_lines:
            line.fish_id.stock_qty -= line.quantity

class OrderLine(models.Model):
    _name = 'order.line'
    _description = 'Order Line'

    order_id = fields.Many2one('order', string='Order', required=True)
    fish_id = fields.Many2one('fish.fish', string='Fish', required=True)
    quantity = fields.Integer(string='Quantity', required=True)
    price = fields.Float(string='Price', compute='_compute_price')

    @api.depends('fish_id', 'quantity')
    def _compute_price(self):
        for line in self:
            line.price = line.fish_id.price * line.quantity

    def _check_available_stock(self):
        for line in self:
            if line.fish_id.stock_qty < line.quantity:
                return False
        return True

    _constraints = [
        (_check_available_stock, 'Insufficient stock for some fishes in the order!', ['quantity']),
    ]

class FishECommerceUser(models.Model):
    _name = 'fish.ecommerce.user'
    _description = 'Fish E-commerce User'

    user_id = fields.Many2one('res.users', string='User', required=True)
    platform_id = fields.Many2one('fish.ecommerce', string='Platform', required=True)
    last_activity_date = fields.Datetime(string='Last Activity Date', default=fields.Datetime.now)

    _sql_constraints = [
        ('unique_user_platform', 'unique (user_id, platform_id)', 'User can only have one active account per platform.'),
    ]

class FishECommerceActivityLog(models.Model):
    _name = 'fish.ecommerce.activity.log'
    _description = 'Fish E-commerce Activity Log'
    _order = 'create_date desc'

    user_id = fields.Many2one('res.users', string='User', required=True)
    activity_type = fields.Selection([('login', 'Login'), ('logout', 'Logout')], string='Activity Type', required=True)
    activity_date = fields.Datetime(string='Activity Date', default=fields.Datetime.now)
    platform_id = fields.Many2one('fish.ecommerce', string='Platform', required=True)

# Additional models and functionalities can be added as per your requirements.

