import numpy as np
import cudarray_wrap.elementwise as wrap
import base


def broadcast_type(shape1, shape2):
    if shape1 == shape2:
        return None

    error = ValueError('operands could not be broadcast together with shapes '
                       + str(shape1) + ' ' + str(shape2))

    # Bring shapes to same length by setting missing trailing dimensions to 1's
    len_diff = len(shape1) - len(shape2)
    if len_diff > 0:
        shape2 = (1,)*len_diff + shape2

    # Find out which axes to broadcast
    b_axes = []
    for a_idx, (a1, a2) in enumerate(zip(shape1, shape2)):
        if a1 != a2:
            if a1 == 1 or a2 == 1:
                b_axes.append(a_idx)
            else:
                raise error

    ndim = len(shape1)
    # Detect leading broadcast
    if b_axes == range(len(b_axes)):
        k = 1
        m = np.prod([shape1[a] for a in b_axes])
        n = np.prod(shape1) // m
        return wrap.btype_leading, k, m, n
    # Detect trailing broadcast
    if b_axes == range(ndim-len(b_axes), ndim):
        k = 1
        m = np.prod([shape1[a] for a in b_axes])
        n = np.prod(shape1) // m
        return wrap.btype_trailing, k, m, n
    # Detect inner broadcast
    if b_axes == range(b_axes[0], b_axes[0] + len(b_axes)):
        k = np.prod(shape1[:b_axes[0]])
        m = np.prod(shape1[b_axes[0]:b_axes[-1]+1])
        n = np.prod(shape1[b_axes[-1]+1:])
        return wrap.btype_inner, k, m, n
    # Detect outer broadcast
    for i in range(1, len(b_axes)):
        if b_axes[i-1] + 1 != b_axes[i]:
            split_idx = i
            break
    b_axes_leading = b_axes[:split_idx]
    b_axes_trailing = b_axes[split_idx:]
    if (b_axes_leading == range(len(b_axes_leading))
            and b_axes_trailing == range(ndim-len(b_axes_trailing), ndim)):
        k = np.prod(shape1[:b_axes_leading[-1]+1])
        m = np.prod(shape1[b_axes_leading[-1]+1:b_axes_trailing[0]])
        n = np.prod(shape1[b_axes_trailing[0]:])
        return wrap.btype_outer, k, m, n

    raise error


def binary(op, x1, x2, out=None, cmp_op=False):
    if np.isscalar(x1) or np.isscalar(x2):
        if np.isscalar(x1):
            scalar = x1
            array = x2
        else:
            array = x1
            scalar = x2

        if (array.dtype == np.dtype('int32') and isinstance(scalar, (int))
                or cmp_op):
            out_dtype = np.dtype('int32')
        else:
            out_dtype = np.dtype('float32')

        # Create/check output array
        if out is None:
            out = base.empty(array.shape, dtype=out_dtype)
        else:
            if out.shape != array.shape:
                raise ValueError('out.shape does not match result')
            if out.dtype != out_dtype:
                raise ValueError('dtype mismatch')
        n = array.size
        if cmp_op:
            wrap._binary_cmp_scalar(op, array._data, scalar, n, out._data)
        else:
            wrap._binary_scalar(op, array._data, scalar, n, out._data)
        return out

    if x1.dtype == x2.dtype == np.dtype('int32') or cmp_op:
        out_dtype = np.dtype('int32')
    else:
        out_dtype = np.dtype('float32')

    # Create/check output array
    if x1.size < x2.size:
        x1, x2 = x2, x1
    if out is None:
        out = base.empty(x1.shape, dtype=out_dtype)
    else:
        if out.shape != x1.shape:
            raise ValueError('out.shape does not match result')
        if out.dtype != out_dtype:
            raise ValueError('dtype mismatch')

    btype = broadcast_type(x1.shape, x2.shape)
    if btype is None:
        n = x1.size
        if cmp_op:
            wrap._binary_cmp(op, x1._data, x2._data, n, out._data)
        else:
            wrap._binary(op, x1._data, x2._data, n, out._data)
        return out
    else:
        btype, k, m, n = btype
        if cmp_op:
            wrap._binary_cmp_broadcast(op, btype, x1._data, x2._data, k, m, n,
                                       out._data)
        else:
            wrap._binary_broadcast(op, btype, x1._data, x2._data, k, m, n,
                                   out._data)
        return out


def add(x1, x2, out=None):
    return binary(wrap.add_op, x1, x2, out)


def subtract(x1, x2, out=None):
    return binary(wrap.sub_op, x1, x2, out)


def multiply(x1, x2, out=None):
    return binary(wrap.mul_op, x1, x2, out)


def divide(x1, x2, out=None):
    return binary(wrap.div_op, x1, x2, out)


def power(x1, x2, out=None):
    return binary(wrap.pow_op, x1, x2, out)


def maximum(x1, x2, out=None):
    return binary(wrap.max_op, x1, x2, out)


def minimum(x1, x2, out=None):
    return binary(wrap.min_op, x1, x2, out)


def equal(x1, x2, out=None):
    return binary(wrap.eq_op, x1, x2, out, True)


def greater(x1, x2, out=None):
    return binary(wrap.gt_op, x1, x2, out, True)


def greater_equal(x1, x2, out=None):
    return binary(wrap.gt_eq_op, x1, x2, out, True)


def less(x1, x2, out=None):
    return binary(wrap.lt_op, x1, x2, out, True)


def less_equal(x1, x2, out=None):
    return binary(wrap.lt_eq_op, x1, x2, out, True)


def not_equal(x1, x2, out=None):
    return binary(wrap.neq_op, x1, x2, out, True)


def unary(op, x, out=None):
    out_shape = x.shape
    if out is None:
        out = base.empty(out_shape, dtype=x.dtype)
    else:
        if not out_shape == out.shape:
            raise ValueError('out.shape does not match result')
        if not x.dtype == out.dtype:
            raise ValueError('dtype mismatch')
    n = x.size
    wrap._unary(op, x._data, n, out._data)
    return out


def absolute(x, out=None):
    return unary(wrap.abs_op, x, out)


def cos(x, out=None):
    return unary(wrap.cos_op, x, out)


def exp(x, out=None):
    return unary(wrap.exp_op, x, out)


def fabs(x, out=None):
    return unary(wrap.abs_op, x, out)


def log(x, out=None):
    return unary(wrap.log_op, x, out)


def negative(x, out=None):
    return unary(wrap.neg_op, x, out)


def sin(x, out=None):
    return unary(wrap.sin_op, x, out)


def sqrt(x, out=None):
    return unary(wrap.sqrt_op, x, out)


def tanh(x, out=None):
    return unary(wrap.tanh_op, x, out)


def clip(a, a_min, a_max, out=None):
    out_shape = a.shape
    if out is None:
        out = base.empty(out_shape, dtype=a.dtype)
    else:
        if not out_shape == out.shape:
            raise ValueError('out.shape does not match result')
        if not a.dtype == out.dtype:
            raise ValueError('dtype mismatch')
    n = a.size
    wrap._clip(a._data, a_min, a_max, n, out._data)
    return out
