from ..route import Route

ROUTES = [
    Route('ticket.create', 'POST', '/api.php/v2/tickets', 'ticket', 'create', required_query=(), required_body=('product', 'title'), enum_values=(('type', ('affair', 'code', 'data', 'security', 'stuck')),)),
    Route('ticket.edit', 'PUT', '/api.php/v2/tickets/{ticketID}', 'ticket', 'edit', required_query=(), required_body=(), enum_values=(('type', ('affair', 'code', 'data', 'security', 'stuck')),)),
    Route('ticket.list_product', 'GET', '/api.php/v2/products/{productID}/tickets', 'ticket', 'list_product', required_query=(), required_body=(), enum_values=(('browseType', ('all', 'assigntome', 'doing', 'done', 'finishedbyme', 'openedbyme', 'unclosed', 'wait')),)),
    Route('ticket.view', 'GET', '/api.php/v2/tickets/{ticketID}', 'ticket', 'view', required_query=(), required_body=(), enum_values=()),
    Route('ticket.close', 'PUT', '/api.php/v2/tickets/{ticketID}/close', 'ticket', 'close', required_query=(), required_body=('closedReason', 'comment'), enum_values=(('closedReason', ('commented', 'refuse', 'repeat')),)),
    Route('ticket.activate', 'PUT', '/api.php/v2/tickets/{ticketID}/activate', 'ticket', 'activate', required_query=(), required_body=(), enum_values=()),
    Route('ticket.delete', 'DELETE', '/api.php/v2/tickets/{ticketID}', 'ticket', 'delete', required_query=(), required_body=(), enum_values=()),
]
