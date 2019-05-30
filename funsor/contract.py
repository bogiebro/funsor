from __future__ import absolute_import, division, print_function

import functools
from collections import OrderedDict

import funsor.interpreter as interpreter
import funsor.ops as ops
from funsor.terms import Funsor, Subs, eager


def _simplify_contract(fn, sum_op, prod_op, lhs, rhs, reduced_vars):
    """
    Reduce free variables that do not appear explicitly in the lhs
    """
    if not reduced_vars:
        return prod_op(lhs, rhs)

    lhs_vars = frozenset(lhs.inputs)
    rhs_vars = frozenset(rhs.inputs)
    assert reduced_vars <= lhs_vars | rhs_vars
    progress = False
    if not reduced_vars <= lhs_vars:
        rhs = rhs.reduce(sum_op, reduced_vars - lhs_vars)
        reduced_vars = reduced_vars & lhs_vars
        progress = True
    if not reduced_vars <= rhs_vars:
        lhs = lhs.reduce(sum_op, reduced_vars - rhs_vars)
        reduced_vars = reduced_vars & rhs_vars
        progress = True
    if progress:
        return Contract(sum_op, prod_op, lhs, rhs, reduced_vars)

    return fn(sum_op, prod_op, lhs, rhs, reduced_vars)


def contractor(fn):
    """
    Decorator for contract implementations to simplify inputs.
    """
    fn = interpreter.debug_logged(fn)
    return functools.partial(_simplify_contract, fn)


class Contract(Funsor):

    def __init__(self, sum_op, prod_op, lhs, rhs, reduced_vars):
        assert isinstance(sum_op, ops.AssociativeOp)
        assert isinstance(prod_op, ops.AssociativeOp)
        assert isinstance(lhs, Funsor)
        assert isinstance(rhs, Funsor)
        assert isinstance(reduced_vars, frozenset)
        inputs = OrderedDict([(k, d) for t in (lhs, rhs)
                              for k, d in t.inputs.items() if k not in reduced_vars])
        output = rhs.output
        fresh = frozenset()
        bound = reduced_vars
        super(Contract, self).__init__(inputs, output, fresh, bound)
        self.sum_op = sum_op
        self.prod_op = prod_op
        self.lhs = lhs
        self.rhs = rhs
        self.reduced_vars = reduced_vars

    def eager_subs(self, subs):
        # basically copied from Reduce.eager_subs
        subs = tuple((k, v) for k, v in subs if k not in self.reduced_vars)
        if not any(k in self.inputs for k, v in subs):
            return self
        if not all(self.reduced_vars.isdisjoint(v.inputs) for k, v in subs):
            raise NotImplementedError('TODO alpha-convert to avoid conflict')
        lhs = Subs(self.lhs, subs)
        rhs = Subs(self.rhs, subs)
        return Contract(self.sum_op, self.prod_op, lhs, rhs, self.reduced_vars)


@eager.register(Contract, ops.AssociativeOp, ops.AssociativeOp, Funsor, Funsor, frozenset)
@contractor
def eager_contract(sum_op, prod_op, lhs, rhs, reduced_vars):
    return prod_op(lhs, rhs).reduce(sum_op, reduced_vars)


__all__ = [
    'Contract',
    'contractor',
]
