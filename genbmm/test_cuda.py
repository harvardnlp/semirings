import torch
from hypothesis import given
from hypothesis.strategies import integers

from .genmul import logbmm

mint = integers(min_value=6, max_value=10)
lint = integers(min_value=0, max_value=10)
sint = integers(min_value=3, max_value=5)

tmp = torch.rand(10).cuda()
@given(sint, mint, mint, mint)
def test_logbmm(batch, row, inner, col):
    a = torch.rand(batch, row, inner, requires_grad=True).cuda()
    b = torch.rand(batch, inner, col, requires_grad=True).cuda()

    c = (a[:, :, :, None] + b[:, None, :, :]).logsumexp(-2)
    c2 = logbmm(a, b)

    assert(torch.isclose(c, c2).all())

    back = torch.rand(batch, row, col, requires_grad=True).cuda()
    g = torch.autograd.grad(c, (a, b), back, create_graph=True)
    g2 = torch.autograd.grad(c2, (a, b), back, create_graph=True)

    for v1, v2 in zip(g, g2):
        assert (torch.isclose(v1, v2).all())


    back2 = (torch.rand(batch, row, inner).cuda(),
             torch.rand(batch, inner, col).cuda())

    c = (a[:, :, :, None] + b[:, None, :, :]).logsumexp(-2)
    g = torch.autograd.grad(c, (a, b), back, create_graph=True)
    h = torch.autograd.grad((g[0], g[1]), (a, b, back), back2)

    c2 = logbmm(a, b)
    g2 = torch.autograd.grad(c2, (a, b), back, create_graph=True)
    h2 = torch.autograd.grad((g2[0], g2[1]), (a, b, back), back2)

    for i, (v1, v2) in enumerate(zip(h, h2)):
        assert torch.isclose(v1, v2, 1e-2).all(), "Round: " + str(i)


from .sparse import banddiag, BandedMatrix
def bmm(a, b):
    return b.multiply(a.transpose())
def bmm_simple(a, b):
    return b.multiply_simple(a.transpose())



@given(sint, mint, lint, lint)
def test_sparse(batch, n, lu, ld):
    start = torch.rand(batch, n, n)
    band, _ = banddiag(start, lu, ld)
    banded_x = BandedMatrix(band, lu, ld)
    x = banded_x.to_dense()

    start = torch.rand(batch, n, n)
    band, _ = banddiag(start, lu, ld)
    banded_y = BandedMatrix(band, lu, ld)
    y = banded_y.to_dense()

    assert torch.isclose(bmm(x, y).data, bmm_simple(x, y).data)
