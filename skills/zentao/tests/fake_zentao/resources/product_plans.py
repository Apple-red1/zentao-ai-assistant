from ..route import Route

ROUTES = [
    Route('product-plan.create', 'POST', '/api.php/v2/productplans', 'product-plan', 'create', required_query=(), required_body=('productID', 'product', 'title'), enum_values=()),
    Route('product-plan.edit', 'PUT', '/api.php/v2/productplans/{planID}', 'product-plan', 'edit', required_query=(), required_body=('productID', 'product', 'title', 'status'), enum_values=(('status', ('wait', 'doing', 'done', 'closed')),)),
    Route('product-plan.list_product', 'GET', '/api.php/v2/products/{productID}/productplans', 'product-plan', 'list_product', required_query=(), required_body=(), enum_values=(('browseType', ('all', 'doing', 'undone', 'wait')),)),
    Route('product-plan.view', 'GET', '/api.php/v2/productplans/{planID}', 'product-plan', 'view', required_query=(), required_body=(), enum_values=()),
    Route('product-plan.delete', 'DELETE', '/api.php/v2/productplans/{planID}', 'product-plan', 'delete', required_query=(), required_body=(), enum_values=()),
]
