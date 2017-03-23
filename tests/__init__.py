import gitkv


def test_class_Repo():
    with gitkv.Repo() as repo:
        repo.os.makedirs('toto')
        res = repo.os.path.exists('toto')
    return res


if __name__ == "__main__":
    import doctest

    doctest.testmod()
