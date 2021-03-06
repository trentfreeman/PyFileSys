import BlockDevice
import os
import numpy 
from struct import *
import math

class FileSystem:

    @staticmethod
    def createFileSystem(filename, numBlocks, sizeBlocks = 1024):
        #This will always create a new file system. 
        #CREATE MASTER BLOCK with settings as given below
        #check if block Size is a power of two with bit manipulation
        if not(sizeBlocks != 0 and ((sizeBlocks &(sizeBlocks-1)) == 0)):
            print("Please make the block size a power of 2")
            return
        if sizeBlocks < numBlocks//8 or sizeBlocks < 128:
            print("Your blocks size is too small to fit either the block map, inodeMap, or the master block. Please make the Block size bigger")
            return
        bd = BlockDevice.BlockDevice(filename, numBlocks, sizeBlocks, True)
        flags = [False] * 8 
        flagArray = numpy.packbits(flags)
        flagBytes = bytearray(flagArray)
        magicNum = 44973
        numInodes = 1
        blkBlockMap = 1
        blkInodeMap = 2
        #Im going to have the data blocks grow backwards. and I nodes grow forwards. This allows the inodes to grow forwards and data backwards.
        blkRoot = numBlocks-1
        buff = bytearray(pack('IHHIIII', magicNum, sizeBlocks, numInodes, numBlocks, blkBlockMap, blkInodeMap, blkRoot))+flagBytes
        bd.write_block(0, buff, True)
        #CREATE BLOCK MAP. Initially it is empty except for the first 3 blocks, which have the master, block map, and inode map respectively 
        #I am just a initiallizing the first 4 bits to 1111 adding the rest of the number of blocks to it using the same method from the flag array 
        blockMap = [True] * 3 + [False] * (numBlocks-4) + [True]
        blockMapArr = numpy.packbits(blockMap)
        BM = bytearray(blockMapArr)
        bd.write_block(1, BM, True)
        #CREATE INODEMAP. The first inode will be the only one to exist initially, so that is the only one to write initially.
        InodeNum = 0
        Cdate = 0
        Mdate = 0
        #flags for each setting: 0xF4 = FR(EE) 244, 0xF1 = FI(LE) 241, 0xD1 = DI(R)209, 0x5b = s(ym)b(olic) link 92, 0xB1 = BL(OCK)177,  0xDA = DA(TA) 218   
        Flag = 244
        Perms = 0
        Level = 0
        padding = 0
        #this has this structure because it the alignment of bytes
        iNodeBytes = bytearray(pack('IIHHBBH', Cdate, Mdate, InodeNum, Perms, Flag, Level, padding))
        #there are 28 possible block pointers, initialize them all to zero (done with a for lop to make more readable)
        iNodeBytes += bytearray(pack('I',0))
        for item in range(1,28):
            iNodeBytes += bytearray(pack('I',0))
        bd.write_block(2, iNodeBytes, True)
        bd.close()




############## BASE FILE SYSTEM METHODS##########################################################################

#init will be called when the command prompt calls mount
    def __init__(self, filename):
        #search for the file
        if not(filename in os.listdir('.')):
            print("Could not find device, please try again")
        self.bd = BlockDevice.BlockDevice(filename)
        readin = bytearray(self.bd.blocksize)
        self.bd.read_block(0, readin)
        #read in all variables from the master block and make them easy to use ints
        (self.magicNum, self.blockSize, self.numInodes, self.numBlocks, self.blockMapNum, self.blockInodeMap, self.blockRoot) = unpack('IHHIIII', readin[0:24])
#set up flag array
        self.flagArray = numpy.unpackbits(bytearray(readin[24:25]))
#check and set dirty bit when mounted
        if self.flagArray[0] == 1:
            print('DID NOT UNMOUNT CORRECTLY LAST MOUNT. CHECK YOUR DATA.')
        self.flagArray[0] = 1 
        #rewrite the block to the masterblock
        readin[24] = numpy.packbits(self.flagArray)[0]
        self.bd.write_block(0,readin,True)
#initialize the blockMap object
        blockMapArr = bytearray(self.blockSize)
        self.bd.read_block(self.blockMapNum, blockMapArr)
        blockMapintArr = numpy.unpackbits(blockMapArr)[0:self.numBlocks]
        self.blockMap = blockMap(blockMapintArr, self.numBlocks)
#initialize the INode array
        iNodeBytes = bytearray()
        buff = bytearray(self.blockSize)
        #if there are more I nodes than fit in a single block, they are in a different block. add that to the byte array.
        for i in range(0, math.ceil(self.numInodes/(self.blockSize/128))):
            self.bd.read_block(self.blockInodeMap+i, buff)
            iNodeBytes += buff
        self.InodeArray = INode.getInodeList(iNodeBytes, self.numInodes)


    def unmount(self):
        #pack the masterblock into bytearray and change the dirty bit back to 0 for false
        self.flagArray[0] = 0
        masterBuff = bytearray(pack('IHHIIII', self.magicNum, self.blockSize, self.numInodes, self.numBlocks, self.blockMapNum, self.blockInodeMap, self.blockRoot))
        masterBuff+= bytearray(numpy.packbits(self.flagArray))
        #NEED TO WRITE MASTER BLOCK LAST, in case unmount fails it is noted
        #Master block written, write out block map
        BMbuff = bytearray(self.blockSize)
        BMbuff = self.blockMap.makeBlockMapByte(self.blockSize)
        self.bd.write_block(1, BMbuff, True)
        #Writing the iNodes back out.
        numInodesInBlock= self.blockSize//128
        iNodeBuff = bytearray()
        count = 0 
        for iNode in self.InodeArray:
            iNodeBuff += iNode.iNodeAsBytes()
            count+=1
            if count % numInodesInBlock == 0:
                #tricky math below, do this to get the index of the block for inodes in order
                self.bd.write_block(self.blockInodeMap + count//numInodesInBlock-1, iNodeBuff, True)
                iNodeBuff = bytearray()
        #it finished all the I nodes but didnt write the last block because it is not full of Inodes
        self.bd.write_block(self.blockInodeMap +count//numInodesInBlock, iNodeBuff, True)
        #write master block last as noted above
        self.bd.write_block(0, masterBuff,True)
        self.bd.close()

            




########## INODE METHOD CALLS  ##################################################################################
    def getInodeMap(self):
        print('| INode # | Flag  |')
        for iNode in self.InodeArray:
            print(iNode.getStatusAsString())
    
    def alloc_INode(self, typeLetter):
        #the current Inode number is one less than the number of Inodes because of array syntax
        InodeNum = self.numInodes
        if self.numInodes%(self.blockSize//128) == 0:
            self.alloc_Block()
        self.numInodes+=1
        Cdate = 0
        Mdate = 0
        #flags for each setting: 0xF4 = FR(EE) 244, 0xF1 = FI(LE) 241, 0xD1 = DI(R)209, 0x5b = s(ym)b(olic) link 92, 0xB1 = BL(OCK)177,  0xDA = DA(TA) 218  
        if typeLetter == '0':
            Flag = 244
        elif typeLetter == 'f':
            Flag = 241
        elif typeLetter == 'd':
            Flag = 209
        elif typeLetter == 's':
            Flag = 92
        elif typeLetter == 'b':
            Flag = 177
        elif typeLetter == 'D':
            Flag = 218
        else:
            print('This letter is undefined, please try again')
            return
        Perms = 0
        Level = 0
        padding = 0
        #this has this structure because it the alignment of bytes
        iNodeBytes = bytearray(pack('IIHHBBH', Cdate, Mdate, InodeNum, Perms, Flag, Level, padding))
        #there are 28 possible block pointers, initialize them all to zero (done with a for lop to make more readable)
        iNodeBytes += bytearray(pack('I',0))
        for item in range(1,28):
            iNodeBytes += bytearray(pack('I',0))
        x = INode(iNodeBytes)
        self.InodeArray += [x]

    def free_INode(self, num):
        if num == 0:
            resp = input("ARE YOU SURE YOU WANT TO FREE THE ROOT INODE? (y/n)")
            if resp == 'n':
                print('Good Choice.')
                return
            elif resp != 'y':
                print('I didnt quite get that. Please try again')
                return
        if num < self.numInodes and num >=0:
            self.InodeArray[num].free()
        else:
            print("This is not a valid inode number. Please try again")



########## BLOCKMAP METHOD CALLS ################################################################################
    def getBlockMap(self):
        self.blockMap.printBlockMap()

    def alloc_Block(self):
        self.blockMap.alloc_block()

    def free_Block(self, num):
        self.blockMap.free_block(num)




########## BLOCK MAP CLASS   ####################################################################################
class blockMap:

    def __init__(self, blockMapArr, numBlocks):
        self.blockMapArr = blockMapArr
        self.numBlocks = numBlocks

    def printBlockMap(self):
        #simple code to print the block map with | every 8 bits and new line every 64
        count = 0 
        for item in self.blockMapArr:
            print(item, end = "")
            count+=1
            if count % 8 == 0 and not(count%64 == 0):
                print('|', end ="")
            if count >= self.numBlocks:
                print("")
                break
            if count%64 == 0:
                print("")
            
    def alloc_block(self):
        count = 0 
        while self.blockMapArr[count] != 0:
            count+=1
        self.blockMapArr[count] = 1
        return count


    def free_block(self, num):
    #dont need to empty data out of block
        if num < 4:
            resp = input('WARNING: THIS IS AN IMPORTANT BLOCK CONTAINING STRUCTURE OF THE FILE SYSTEM. ARE YOU SURE YOU WANT TO DELETE THIS BLOCK? (y/n)')
            if resp == 'n':
                return
            elif resp != 'y':
                print("I didn't quite get that. Could you please repeat the command?")
                return
        elif num > self.numBlocks:
            print("You cannot free a block that doesen't exist. Please Try again")
            return
        self.blockMapArr[num-1] = 0
        print('Block Freed')

    def makeBlockMapByte(self, sizeBlock):
        arr = numpy.packbits(self.blockMapArr)
        return bytearray(arr)
        






########### INODE CLASS   #########################################################################################
class INode:

    @staticmethod
    def getInodeList(INodeBytes, numINodes):
        retArr = [INode(INodeBytes[i*128:(i+1)*128]) for i in range(0,numINodes)]
        return retArr

    def __init__(self, iNodeBlock):
        (self.Cdate, self.Mdate, self.InodeNum, self.Perms, self.Flag, self.Level, self.padding) = unpack("IIHHBBH", iNodeBlock[0:16])
        self.data = iNodeBlock[16:]

    def getStatusAsString(self):
        #flags for each setting: 0xF4 = FR(EE) 244, 0xF1 = FI(LE) 241, 0xD1 = DI(R)209, 0x5b = s(ym)b(olic) link 92, 0xB1 = BL(OCK)177,  0xDA = DA(TA) 218 
        retString = "|   " +str(self.InodeNum)+"     |"
        if self.Flag == 244:
            retString+= '   0   |'
        elif self.Flag == 241:
            retString+= '   f   |'
        elif self.Flag == 209:
            retString+= '   d   |'
        elif self.Flag == 92:
            retString+= '   s   |'
        elif self.Flag == 218:
            retString+= '   D   |'
        elif self.Flag ==177:
            retString+= '   b   |'
        return retString

    def iNodeAsBytes(self):
        retBytes = bytearray()
        retBytes = bytearray(pack('IIHHBBH', self.Cdate, self.Mdate, self.InodeNum, self.Perms, self.Flag, self.Level, self.padding))
        retBytes += self.data
        return retBytes

    def free(self):
        self.Flag = 244




############ TESTING      #######################################################################################
def test_Simple():
    bSize = 1024
    blocks = 200
    FileSystem.createFileSystem('testing123', blocks)
    fs = FileSystem('testing123.dev')
    assert fs.blockSize == bSize, "didn't initialize block size correctly"
    assert fs.numBlocks == blocks, "num of blocks not correct"
    for i in range(0,30):
        fs.alloc_Block()
    assert numpy.count_nonzero(fs.blockMap.blockMapArr == 1) == 34, "not allocating block correctly"
    symbList = [244]
    numList = [244, 241, 209, 92, 177, 218]
    for i in range(0,15):
        symb = ['0', 'f', 'd', 's', 'b', 'D'][i %6]
        fs.alloc_INode(symb)
        symbList += [numList[i%6]]
    for i in range(0,16):
        assert fs.InodeArray[i].InodeNum == i, 'not initializing Inodes correctly'
        assert fs.InodeArray[i].Flag == symbList[i], 'not initializing Inode flags correctly'
