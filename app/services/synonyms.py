import rowordnet

WORDNET = rowordnet.RoWordNet()


def get_synonyms(token):
    if not token.is_alpha or (len(token.text) < 4):
        return []
    lexem_literal = sum(
        [
            WORDNET.synset(synset_id).literals
            for synset_id in WORDNET.synsets(literal=token.text)
        ],
        [],
    )
    lemma_literal = sum(
        [
            WORDNET.synset(synset_id).literals
            for synset_id in WORDNET.synsets(literal=token.lemma_)
        ],
        [],
    )
    all_literals = set(lemma_literal + lexem_literal)
    synonyms = []
    for literal in all_literals:
        if token.text not in literal and "_" not in literal:
            synonyms.append(literal)
    return list(set(synonyms))
