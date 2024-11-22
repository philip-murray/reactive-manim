from .dynamic_tex_mobject import *

def frac_sum(*fractions: Fraction):

    fractions = list(fractions)

    if len(fractions) < 2:
        raise Exception()
    
    for term in fractions:
        if not isinstance(term, Fraction):
            raise Exception("All input to frac_sum() must be of type Fraction")
    

# requirements for distribute
# same mul-group
# +[a(x+y)] -> +[ax]+[ay]
# -[a(x+y)] -> -[ax]-[ay] # minus-style-1
# -[a(x-y)] -> -[ax]+[ay] # where does
# -[a(x-y)] -> -[ax]-[a(-y)] # 
    
def distribute_term(
    term: MathEncodable,
    partial: MathEncodable,
    combine=False,
    index=0
):
    pass
        
    

def distribute(
    term: MathEncodable, 
    parentheses: Parentheses,
    combine=True,
    index=0,
    drop_parentheses=True
):
    pass

