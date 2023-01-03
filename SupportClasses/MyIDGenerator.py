class IDs:
    def __init__(self, minID : int, maxID : int = -1, step = 1):
        self.minID = minID
        self.maxID = maxID
        self.step = step
        self.ID_free_list = []

    def get_ID(self):
        if len(self.ID_free_list) > 0:
            return self.ID_free_list.pop()
        else:
            if self.maxID != -1 and self.minID > self.maxID:
                return -1
            else:
                ID = self.minID
                self.minID += self.step
                return int(ID)

    def free_ID(self, ID : int):
        self.ID_free_list.append(ID)